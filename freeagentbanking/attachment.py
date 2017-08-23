from os.path import basename, splitext
import base64


class Attachment(object):
    CONTENT_TYPES = {
        # See https://dev.freeagent.com/docs/expenses#create-an-expense
        '.pdf': 'application/x-pdf',
    }

    def __init__(self, abs_filename):
        self.filename = abs_filename

    def serialize(self):
        return {
            'file_name': basename(self.filename),
            'content_type': self.content_type,
            'data': self.base64_data,
        }

    @property
    def content_type(self):
        _, extension = splitext(self.filename)
        return self.CONTENT_TYPES[extension]

    @property
    def base64_data(self):
        with open(self.filename, 'rb') as f:
            return base64.b64encode(f.read()).decode('ascii')
