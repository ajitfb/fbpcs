# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict

import os
from typing import Iterable
from unittest import TestCase
from unittest.mock import patch, MagicMock, Mock

from fbpcs.input_data_validation.constants import INPUT_DATA_TMP_FILE_PATH
from fbpcs.input_data_validation.enums import ValidationResult
from fbpcs.input_data_validation.validation_runner import ValidationRunner
from fbpcs.private_computation.entity.cloud_provider import CloudProvider

TEST_INPUT_FILE_PATH = "s3://test-bucket/data.csv"
TEST_REGION = "us-west-2"
TEST_TIMESTAMP = 1644538741.077141
TEST_TEMP_FILEPATH = f"{INPUT_DATA_TMP_FILE_PATH}/data.csv-{TEST_TIMESTAMP}"


class TestValidationRunner(TestCase):
    def setUp(self) -> None:
        open(TEST_TEMP_FILEPATH, "a").close()

    def tearDown(self) -> None:
        os.remove(TEST_TEMP_FILEPATH)

    def write_lines_to_file(self, lines: Iterable[bytes]) -> None:
        with open(TEST_TEMP_FILEPATH, "wb") as tmp_csv_file:
            tmp_csv_file.writelines(lines)

    @patch("fbpcp.service.storage_s3.S3StorageService")
    def test_initializating_the_validation_runner_fields(self, _mock) -> None:
        cloud_provider = CloudProvider.AWS

        validation_runner = ValidationRunner(
            TEST_INPUT_FILE_PATH, cloud_provider, "us-west-2"
        )

        self.assertEqual(validation_runner._input_file_path, TEST_INPUT_FILE_PATH)
        self.assertEqual(validation_runner._cloud_provider, cloud_provider)

    @patch("fbpcs.input_data_validation.validation_runner.S3StorageService")
    def test_initializing_the_validation_runner_storage_service(
        self, mock_storage_service: Mock
    ) -> None:
        cloud_provider = CloudProvider.AWS
        access_key_id = "id1"
        access_key_data = "data2"
        region = "us-east-2"
        constructed_storage_service = MagicMock()
        mock_storage_service.__init__(return_value=constructed_storage_service)

        validation_runner = ValidationRunner(
            TEST_INPUT_FILE_PATH, cloud_provider, region, access_key_id, access_key_data
        )

        mock_storage_service.assert_called_with(region, access_key_id, access_key_data)
        self.assertEqual(
            validation_runner._storage_service, constructed_storage_service
        )

    @patch("fbpcs.input_data_validation.validation_runner.S3StorageService")
    def test_run_validations_failure(self, storage_service_mock: Mock) -> None:
        exception_message = "failed to copy"
        input_file_path = "s3://test-bucket/data.csv"
        cloud_provider = CloudProvider.AWS
        expected_report = {
            "status": ValidationResult.FAILED.value,
            "message": f"File: {input_file_path} failed validation. Error: {exception_message}",
            "rows_processed_count": "0",
        }
        storage_service_mock.__init__(return_value=storage_service_mock)
        storage_service_mock.copy.side_effect = Exception(exception_message)

        validation_runner = ValidationRunner(
            input_file_path, cloud_provider, "us-west-2"
        )
        report = validation_runner.run()

        self.assertDictEqual(report, expected_report)

    @patch("fbpcs.input_data_validation.validation_runner.S3StorageService")
    @patch("fbpcs.input_data_validation.validation_runner.time")
    def test_run_validations_reads_the_local_csv_rows(
        self, time_mock: Mock, _storage_service_mock: Mock
    ) -> None:
        time_mock.time.return_value = TEST_TIMESTAMP
        cloud_provider = CloudProvider.AWS
        lines = [
            b"id_,value,timestamp\n",
            b"abcd/1234+WXYZ=,100,1645157987\n",
            b"abcd/1234+WXYZ=,100,1645157987\n",
            b"abcd/1234+WXYZ=,100,1645157987\n",
        ]
        self.write_lines_to_file(lines)
        expected_report = {
            "status": ValidationResult.SUCCESS.value,
            "message": f"File: {TEST_INPUT_FILE_PATH} was validated successfully",
            "rows_processed_count": "3",
        }

        validation_runner = ValidationRunner(
            TEST_INPUT_FILE_PATH, cloud_provider, TEST_REGION
        )
        report = validation_runner.run()

        self.assertDictEqual(report, expected_report)
