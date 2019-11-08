"""
    This class is a very particular strace output parser.
    It extracts the path from an open statement
"""
class STraceParser:
    def __init__(self, line):
        self.line = line

    # This is sorry excuse for a parser, but simplest thing I can hide behind an abstraction for now
    def get_path(self):
        #openat(AT_FDCWD, "t2.txt", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 3\n
        split_strace_output = self.line.split('"')
        if len(split_strace_output) < 2:
            raise WrongSTraceFormatException

        return split_strace_output[1]



class WrongSTraceFormatException(Exception):
    pass