import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import main


class RepoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.tmp.name)
        self.git('init', '-q')

    def tearDown(self):
        os.chdir(self.previous)
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(['git', *args], check=True, capture_output=True)

    def base(self):
        Path('app.py').write_text('value = 1\n')
        self.git('add', 'app.py')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 'commit', '-qm', 'baseline')

    def args(self, *extra):
        return main.parser().parse_args(['commit', *extra])

    def test_clean_repo_does_not_call_api_or_require_key(self):
        self.base()
        with patch.dict(os.environ, {}, clear=True), patch('main.request_ai') as api:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(['commit']), 0)
            api.assert_not_called()

    def test_staged_and_unstaged_are_collected(self):
        self.base()
        Path('app.py').write_text('value = 2\n')
        self.git('add', 'app.py')
        Path('app.py').write_text('value = 3\n')
        diff = main.collect(self.args())['diff']
        self.assertIn('STAGED', diff)
        self.assertIn('UNSTAGED', diff)
        self.assertIn('+value = 2', diff)
        self.assertIn('+value = 3', diff)

    def test_unborn_repo_staged_file(self):
        Path('new file.py').write_text('print(42)\n')
        self.git('add', '.')
        self.assertIn('+print(42)', main.collect(self.args())['diff'])

    def test_untracked_content_is_not_invented(self):
        Path('new.py').write_text('unseen content')
        context = main.collect(self.args())
        self.assertIn('내용 미수집', context['diff'])
        self.assertNotIn('unseen content', context['diff'])

    def test_sensitive_files_excluded_even_if_tracked(self):
        Path('.env').write_text('password=should-never-send\n')
        Path('safe.py').write_text('pass\n')
        self.git('add', '.')
        for extra in [[], ['--no-safe-mode']]:
            context = main.collect(self.args(*extra))
            self.assertEqual(context['excluded_count'], 1)
            self.assertNotIn('should-never-send', json.dumps(context))

    def test_masking_applies_to_diff_filenames_and_reason(self):
        Path('person@example.com.py').write_text('token = "fake-secret-value"\n')
        self.git('add', '.')
        context = main.collect(self.args('--reason', 'contact person@example.com'))
        encoded = json.dumps(context)
        self.assertNotIn('person@example.com', encoded)
        self.assertNotIn('fake-secret-value', encoded)

    def test_safe_mode_limits_and_off_comparison(self):
        for name in ['a.py', 'b.py']:
            Path(name).write_text('\n'.join(str(n) for n in range(30)))
        self.git('add', '.')
        limited = main.collect(self.args('--max-files', '1', '--max-lines', '10'))
        full = main.collect(self.args('--no-safe-mode'))
        self.assertEqual(len(limited['files']), 1)
        self.assertEqual(limited['omitted_files'], 1)
        self.assertTrue(limited['diff_truncated'])
        self.assertEqual(len(full['files']), 2)
        self.assertFalse(full['diff_truncated'])

    def test_rename_and_literal_path(self):
        self.base()
        self.git('mv', 'app.py', ':(glob)*.py')
        context = main.collect(self.args())
        self.assertEqual(context['files'][0]['old_path'], 'app.py')
        self.assertIn('rename to :(glob)*.py', context['diff'])

    def test_partial_private_key_is_masked_before_truncation(self):
        Path('config.txt').write_text('-----BEGIN PRIVATE KEY-----\n' +
                                      'hidden-key-material\n' * 40 +
                                      '-----END PRIVATE KEY-----\n')
        self.git('add', '.')
        context = main.collect(self.args('--max-lines', '8'))
        self.assertNotIn('hidden-key-material', json.dumps(context))

    def test_end_to_end_cli_with_mock_http(self):
        self.base()
        Path('app.py').write_text('value = 2\n')
        answer = {**PR, 'commit': COMMIT}
        response = io.StringIO(json.dumps({'choices': [{'finish_reason': 'stop',
                                                       'message': {'content': json.dumps(answer)}}]}))
        with patch.dict(os.environ, {'AI_API_KEY': 'test-only-not-a-real-key'}), \
             patch('urllib.request.urlopen', return_value=response) as api, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main.main(['all']), 0)
            self.assertEqual(api.call_count, 1)
            self.assertIn('Commit Message', output.getvalue())
            self.assertIn('## How to Test', output.getvalue())
            payload = json.loads(api.call_args.args[0].data)
            self.assertIn('+value = 2', payload['messages'][1]['content'])

    def test_subdirectory_rejected(self):
        Path('child').mkdir()
        os.chdir('child')
        with self.assertRaises(main.AppError):
            main.collect(self.args())

    def test_preview_does_not_call_api(self):
        Path('new.py').write_text('pass')
        with patch('main.request_ai') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.main(['commit', '--preview']), 0)
            api.assert_not_called()

    def test_missing_key(self):
        Path('new.py').write_text('pass')
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(main.main(['commit']), 1)
            self.assertIn('AI_API_KEY', err.getvalue())


COMMIT = {'summary': '変更要約', 'title': 'feat: 입력 검증 추가', 'body': '- 잘못된 입력 거부'}
PR = {'summary': '입력 검증', 'title': 'feat: 입력 검증 추가',
      'why': ['잘못된 입력 방지'], 'what': ['검증 추가'],
      'how_to_test': ['잘못된 입력으로 실행해 거부 확인']}


class GenerationTest(unittest.TestCase):
    def args(self, command='commit'):
        return main.parser().parse_args([command])

    def test_title_and_section_validation(self):
        for data, command in [({**COMMIT, 'title': 'x' * 73}, 'commit'),
                              ({**COMMIT, 'title': 'one\ntwo'}, 'commit'),
                              ({**COMMIT, 'body': 'no bullet'}, 'commit'),
                              ({**PR, 'title': 'x' * 81}, 'pr'),
                              ({**PR, 'why': []}, 'pr'),
                              ({**PR, 'what': ['']}, 'pr')]:
            with self.subTest(command=command, data=data):
                with self.assertRaises(main.AppError):
                    main.validate(data, command)

    def test_retry_limit_and_successful_repair(self):
        with patch('main.request_ai', side_effect=['{}', json.dumps(COMMIT)]) as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.generate({}, self.args(), 'fake')['title'], COMMIT['title'])
            self.assertEqual(api.call_count, 2)
        with patch('main.request_ai', return_value='{}') as api, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(main.AppError):
                main.generate({}, self.args(), 'fake')
            self.assertEqual(api.call_count, 2)

    def test_all_uses_one_request_and_renders_both(self):
        result = {**PR, 'commit': COMMIT}
        with patch('main.request_ai', return_value=json.dumps(result)) as api, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main.run_all({}, self.args('all'), 'fake'), 0)
            self.assertEqual(api.call_count, 1)
            for header in ['Commit Message', 'PR Title', '## Why', '## What', '## How to Test']:
                self.assertIn(header, output.getvalue())

    def test_rest_payload_and_response(self):
        response = io.StringIO(json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(COMMIT)}}]}))
        with patch('urllib.request.urlopen', return_value=response) as urlopen:
            self.assertIn('title', main.request_ai([], self.args(), 'fake-key'))
            request = urlopen.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload['temperature'], 0.2)
            self.assertEqual(payload['max_completion_tokens'], 1500)
            self.assertFalse(payload['store'])
            self.assertEqual(request.full_url, main.ENDPOINT)

    def test_http_error_has_reason_without_leaking_response(self):
        for code in (400, 401, 403, 404, 429, 500):
            err = urllib.error.HTTPError(main.ENDPOINT, code, 'secret server body', {}, None)
            with self.subTest(code=code), patch('urllib.request.urlopen', side_effect=err):
                with self.assertRaises(main.AppError) as caught:
                    main.request_ai([], self.args(), 'fake')
                self.assertIn(str(code), str(caught.exception))
                self.assertNotIn('secret', str(caught.exception))

    def test_invalid_header_key_is_not_sent_or_printed(self):
        with patch('urllib.request.urlopen') as api:
            with self.assertRaises(main.AppError) as caught:
                main.request_ai([], self.args(), 'private-key\n')
            self.assertNotIn('private-key', str(caught.exception))
            api.assert_not_called()

    def test_masked_title_is_validated_before_output(self):
        result = {**COMMIT, 'title': 'a@b.co ' + 'x' * 65}
        with patch('main.request_ai', return_value=json.dumps(result)) as api, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(main.AppError):
                main.generate({}, self.args(), 'fake')
            self.assertEqual(api.call_count, 2)

    def test_network_and_truncated_output_fail(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('private context')):
            with self.assertRaisesRegex(main.AppError, '네트워크'):
                main.request_ai([], self.args(), 'fake')
        response = io.StringIO(json.dumps({'choices': [{'finish_reason': 'length'}]}))
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(main.AppError, '토큰'):
                main.request_ai([], self.args(), 'fake')

    def test_private_key_and_terminal_controls(self):
        self.assertNotIn('hidden', main.mask('-----BEGIN PRIVATE KEY-----\nhidden\n-----END PRIVATE KEY-----'))
        self.assertNotIn('\x1b', main.terminal('\x1b[31mred'))


if __name__ == '__main__':
    unittest.main()
