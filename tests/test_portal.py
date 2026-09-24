import unittest

from troika_d_lite.portal import portal_response_is_cancelled


class PortalPolicyTests(unittest.TestCase):
    def test_code_1_is_normal_user_cancel(self):
        self.assertTrue(portal_response_is_cancelled(1))

    def test_other_codes_are_not_cancel(self):
        for code in (None, 0, 2, 3):
            self.assertFalse(portal_response_is_cancelled(code))


if __name__ == "__main__":
    unittest.main()
