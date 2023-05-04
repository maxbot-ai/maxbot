"""Download file utils."""
import mimetypes
import os
import re
import tempfile
import uuid
from contextlib import asynccontextmanager

import httpx

HTTPX_CLIENT = httpx.AsyncClient(timeout=30)
TMP_FILE_MAX_SIZE = 1024 * 1024  # in bytes
DEFAULT_CHUNK_SIZE = 512  # in bytes


class DownloadResult:
    """Download result class."""

    def __init__(self, temp_file, response):
        """Create a new class instance.

        :param tempfile.SpooledTemporaryFile temp_file: Temporary file wrapper
        :param dict requests.models.Response: Object, which contains a server's response to an HTTP request.
        """
        self.temp_file = temp_file
        self.response = response

    def get_filename_from_content_disposition(self):
        """Return filename from headers['Content-Disposition'] if it has extension."""
        filename = re.findall(
            "filename=(.+)", self.response.headers.get("Content-Disposition", "")
        )
        return filename[0] if filename and len(filename[0].split(".")) > 1 else None

    def get_filename_from_content_type(self):
        """Return random filename and extension from headers['content-type']."""
        img_ext = mimetypes.guess_extension(self.response.headers["content-type"])
        return f"{uuid.uuid4()}{img_ext}"

    def get_filename_from_url(self):
        """Return filename from url if it has extension."""
        filename = os.path.basename(self.response.url.path)
        return filename if len(filename.split(".")) > 1 else None

    def determine_filename(self):
        """Return filename.

        Get filename from headers['Content-Disposition'] or url
        or random filename and extension from headers['content-type']
        """
        filename = self.get_filename_from_content_disposition()
        if not filename:
            filename = self.get_filename_from_url()
        if not filename:
            filename = self.get_filename_from_content_type()
        return filename


@asynccontextmanager
async def download_to_tempfile(url):
    """Download remote file into temporary file.

    . code-block:: python

        with download_to_tempfile(url) as r:
            print(r.response.headers['content-type'])
            print('File size:', len(r.temp_file.read()))

    :param str url: File url
    :return DownloadResult: A container temporary file and request response.
    """
    with tempfile.SpooledTemporaryFile(max_size=TMP_FILE_MAX_SIZE) as temp_file:
        async with HTTPX_CLIENT.stream("GET", url) as response:
            async for chunk in response.aiter_bytes(DEFAULT_CHUNK_SIZE):
                temp_file.write(chunk)
            temp_file.seek(0)
            yield DownloadResult(temp_file, response)
