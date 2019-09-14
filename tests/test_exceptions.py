import unittest
import redexpect

class RedExpectUnitTest(unittest.TestCase):

    def test_bad_sudo_password(self):
        redexpect.exceptions.BadSudoPassword()

    def test_expect_timeout(self):
        redexpect.exceptions.ExpectTimeout(None)


if __name__ == '__main__':
    unittest.main()

