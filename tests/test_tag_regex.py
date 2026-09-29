import tempfile
import unittest
from pathlib import Path
from unittest import mock

import entrypoint


class TestTagRegex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.stack = Path(self.tmp.name) / 'values.yaml'
        with mock.patch('entrypoint.subprocess'):
            self.cli = entrypoint.CLI(None, None, '*.yaml', None, None, None, None)
        self.cli.repo_dir = Path(self.tmp.name)
        self.cli.branches = ''
        self.tags = mock.patch('entrypoint.get_tags', return_value=['4.1.0', '4.1.2', '2021.11.18']).start()
        self.addCleanup(mock.patch.stopall)

    def write(self, text):
        self.stack.write_text(text)

    def update(self, data):
        with mock.patch.object(self.cli, 'create_branch_and_mr'), mock.patch('entrypoint.subprocess'):
            self.cli.update_stack(self.stack, data)
        return self.stack.read_text()

    def test_transmission_split_jsonpath(self):
        self.cli._image_jsonpath = 'deployment.image.repository'
        self.cli._tag_jsonpath = 'deployment.image.tag'
        self.write(
            'deployment:\n  image:\n    repository: linuxserver/transmission\n'
            '    # autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\n    tag: "4.1.1"\n'
            'other:\n  tag: "4.1.1"\n'
        )
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(data[0][1], [((4, 1, 2), '4.1.2')])
        result = self.update(data)
        self.assertIn('    tag: "4.1.2"', result)
        self.assertIn('other:\n  tag: "4.1.1"', result)
        self.assertIn('# autoupdater: tag-regex=\\d\\.\\d+\\.\\d+', result)

    def test_identical_images_have_independent_filters_and_updates(self):
        self.write(
            'a:\n  # autoupdater: tag-regex=4\\.1\\.1\n  image: app:4.1.1\n'
            'b:\n  # autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\n  image: app:4.1.1\n'
            'c:\n  # autoupdater: disable\n  image: app:4.1.1\n'
        )
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0][1], [])
        self.assertEqual(data[1][1], [((4, 1, 2), '4.1.2')])
        result = self.update(data)
        self.assertEqual(result.count('image: app:4.1.1'), 2)
        self.assertEqual(result.count('image: app:4.1.2'), 1)

    def test_mapped_field_filters_complete_tag(self):
        with mock.patch('entrypoint.subprocess'):
            self.cli = entrypoint.CLI(None, None, '', {'version': 'app:v?-alpine'}, None, None, None)
        self.cli.repo_dir = Path(self.tmp.name)
        self.cli.branches = ''
        self.tags.return_value = ['v4.1.2-alpine', 'v2021.11.18-alpine', 'v4.2.0']
        self.write(
            'a:\n  # autoupdater: tag-regex=v\\d\\.\\d+\\.\\d+-alpine\n  version: 4.1.1\n'
            'b:\n  # autoupdater: disable\n  version: 4.1.1\n'
        )
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(data, [(('version: ', '4.1.1'), [((4, 1, 2), '4.1.2')])])
        self.assertIn('b:\n  # autoupdater: disable\n  version: 4.1.1', self.update(data))

    def test_mapped_field_without_suffix(self):
        with mock.patch('entrypoint.subprocess'):
            cli = entrypoint.CLI(None, None, '', {'version': 'app:?'}, None, None, None)
        cli.repo_dir = self.cli.repo_dir
        self.write('# autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\nversion: 4.1.1\n')
        self.assertEqual(cli.proc_stack(self.stack)[0][1], [((4, 1, 2), '4.1.2')])

    def test_jsonpath_combined_and_sequence(self):
        self.cli._image_jsonpath = 'apps[*].repository'
        self.write(
            'apps:\n  - # ordinary comment\n    # autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\n'
            '    repository: app:4.1.1\n  - repository: app:4.1.1\n'
        )
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(data[0][1], [((4, 1, 2), '4.1.2')])
        self.assertEqual(data[1][1][-1], ((2021, 11, 18), '2021.11.18'))
        result = self.update(data)
        self.assertIn('    repository: app:4.1.2', result)
        self.assertIn('  - repository: app:2021.11.18', result)

    def test_filter_does_not_change_extraction_or_ordering(self):
        self.tags.return_value = [
            'v4.1.2-python3.12',
            'v4.1.10-python3.12',
            'v4.1.20-python3.13',
            'v4.2-python3.12',
            'v2021.11.18-python3.12',
        ]
        result = self.cli.check_image(self.stack, 'app', 'v4.1.1-python3.12', r'v\d\..*')
        self.assertEqual(result, [((4, 1, 2), 'v4.1.2-python3.12'), ((4, 1, 10), 'v4.1.10-python3.12')])
        self.tags.return_value = ['2024-02-01', '2024-10-01']
        self.assertEqual(
            self.cli.check_image(self.stack, 'app', '2024-01-01', r'2024-\d+-\d+')[-1], ((2024, 10, 1), '2024-10-01')
        )

    def test_no_filter_preserves_behavior(self):
        self.assertEqual(self.cli.check_image(self.stack, 'app', '4.1.1')[-1], ((2021, 11, 18), '2021.11.18'))

    def test_invalid_mismatched_empty_and_duplicate_filters(self):
        for directive, error in [
            ('tag-regex=[', 'invalid autoupdater tag-regex'),
            ('tag-regex=3\\..*', 'current tag'),
            ('tag-regex=', 'current tag'),
            ('tag-regex=4\\.1', 'current tag'),
            ('tag-regex=.*\n# autoupdater: tag-regex=.*', 'multiple'),
        ]:
            with self.subTest(directive=directive):
                self.write(f'# autoupdater: {directive}\nimage: app:4.1.1\n')
                with self.assertRaisesRegex(ValueError, error):
                    self.cli.proc_stack(self.stack)
        self.tags.assert_not_called()

    def test_disable_takes_precedence_over_invalid_filter(self):
        self.write('# autoupdater: disable\n# autoupdater: tag-regex=[\nimage: app:4.1.1\n')
        self.assertEqual(self.cli.proc_stack(self.stack), [])
        self.tags.assert_not_called()

    def test_filter_scope_ends_at_blank_line_or_other_field(self):
        for separator in ['\n', 'another: value\n']:
            with self.subTest(separator=separator):
                self.write('# autoupdater: tag-regex=[\n' + separator + 'image: app:4.1.1\n')
                self.assertEqual(self.cli.proc_stack(self.stack)[0][1][-1], ((2021, 11, 18), '2021.11.18'))

    def test_quoted_anchored_image(self):
        self.write('# autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\nimage: &app "app:4.1.1"\n')
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(data[0][1], [((4, 1, 2), '4.1.2')])
        self.assertIn('image: &app "app:4.1.2"', self.update(data))

    def test_jsonpath_sequence_tag(self):
        self.cli._image_jsonpath = 'repository'
        self.cli._tag_jsonpath = 'tags[0]'
        self.write('repository: app\ntags:\n  # autoupdater: tag-regex=\\d\\.\\d+\\.\\d+\n  - "4.1.1"\n')
        data = self.cli.proc_stack(self.stack)
        self.assertEqual(data[0][1], [((4, 1, 2), '4.1.2')])
        self.assertIn('  - "4.1.2"', self.update(data))

    def test_bad_filter_fails_file_in_dry_and_real_runs(self):
        original = 'image: other:4.1.1\napp:\n  # autoupdater: tag-regex=[\n  image: app:4.1.1\n'
        self.write(original)
        with mock.patch.object(self.cli, 'setup_git'), mock.patch.object(self.cli, 'create_branch_and_mr') as create:
            self.assertEqual(self.cli.dry_run(), 1)
            self.assertEqual(self.cli.run(), 1)
        create.assert_not_called()
        self.assertEqual(self.stack.read_text(), original)

    def test_no_allowed_newer_tags(self):
        self.tags.return_value = ['2021.11.18', '4.1.0', '4.1.1']
        self.assertEqual(self.cli.check_image(self.stack, 'app', '4.1.1', r'\d\.\d+\.\d+'), [])

    def test_fullmatch_filters_candidate_tail(self):
        self.tags.return_value = ['4.1.2', '4.1.20']
        self.assertEqual(self.cli.check_image(self.stack, 'app', '4.1.1', r'4\.1\.\d'), [((4, 1, 2), '4.1.2')])
