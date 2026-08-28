import unittest
from unittest.mock import Mock, mock_open, patch

from receiver.dicomweb import _retrieve_instance


def _response(status, content=b"", content_type=""):
    resp = Mock()
    resp.status_code = status
    resp.content = content
    resp.headers = {"Content-Type": content_type} if content_type else {}
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        resp.raise_for_status.return_value = None
    return resp


class RetrieveInstanceAcceptTest(unittest.TestCase):
    def test_retries_multipart_accept_after_406(self):
        dicom_body = b"\x00" * 200
        not_acceptable = _response(406)
        ok = _response(
            200,
            content=dicom_body,
            content_type="application/dicom",
        )

        session = Mock()
        session.get.side_effect = [not_acceptable, ok]

        with patch("receiver.dicomweb.os.makedirs"):
            with patch("builtins.open", mock_open()):
                count = _retrieve_instance(
                    session,
                    "https://pacs.example/wado",
                    "1.2.3",
                    "1.2.4",
                    "1.2.5",
                    "/tmp/out",
                )

        self.assertEqual(count, 1)
        first_accept = session.get.call_args_list[0].kwargs["headers"]["Accept"]
        second_accept = session.get.call_args_list[1].kwargs["headers"]["Accept"]
        self.assertIn("multipart/related", first_accept)
        self.assertIn("application/dicom", first_accept)
        self.assertNotEqual(first_accept, second_accept)
        self.assertEqual(session.get.call_count, 2)
