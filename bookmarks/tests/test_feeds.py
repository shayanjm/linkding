import datetime
import email
import unittest
import urllib.parse

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from bookmarks.feeds import sanitize
from bookmarks.models import FeedToken, User
from bookmarks.tests.helpers import BookmarkFactoryMixin


def rfc2822_date(date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.combine(date, datetime.time())
    return email.utils.format_datetime(date)


class FeedsTestCase(TestCase, BookmarkFactoryMixin):
    def setUp(self) -> None:
        user = self.get_or_create_test_user()
        self.client.force_login(user)
        self.token = FeedToken.objects.get_or_create(user=user)[0]

    def assertFeedItems(self, response, bookmarks):
        self.assertContains(response, "<item>", count=len(bookmarks))

        for bookmark in bookmarks:
            categories = []
            for tag in bookmark.tag_names:
                categories.append(f"<category>{tag}</category>")

            if bookmark.resolved_description:
                expected_description = (
                    f"<description>{bookmark.resolved_description}</description>"
                )
            else:
                expected_description = "<description/>"

            expected_item = (
                "<item>"
                f"<title>{bookmark.resolved_title}</title>"
                f"<link>{bookmark.url}</link>"
                f"{expected_description}"
                f"<pubDate>{rfc2822_date(bookmark.date_added)}</pubDate>"
                f"<guid>{bookmark.url}</guid>"
                f"{''.join(categories)}"
                "</item>"
            )
            self.assertContains(response, expected_item, count=1)

    def test_all_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("linkding:feeds.all", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_all_metadata(self):
        feed_url = reverse("linkding:feeds.all", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>All bookmarks</title>")
        self.assertContains(response, "<description>All bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_all_returns_all_unarchived_bookmarks(self):
        bookmarks = [
            self.setup_bookmark(description="test description"),
            self.setup_bookmark(description=""),
            self.setup_bookmark(unread=True, description="test description"),
        ]
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)
        self.setup_bookmark(is_archived=True)

        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, bookmarks)

    def test_all_returns_only_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)

        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<item>", count=0)

    def test_unread_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("linkding:feeds.unread", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_unread_metadata(self):
        feed_url = reverse("linkding:feeds.unread", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Unread bookmarks</title>")
        self.assertContains(response, "<description>All unread bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_unread_returns_unread_and_unarchived_bookmarks(self):
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=True, is_archived=True)
        self.setup_bookmark(unread=True, is_archived=True)
        self.setup_bookmark(unread=False, is_archived=True)

        unread_bookmarks = [
            self.setup_bookmark(unread=True, description="test description"),
            self.setup_bookmark(unread=True, description=""),
            self.setup_bookmark(unread=True, description="test description"),
        ]

        response = self.client.get(
            reverse("linkding:feeds.unread", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, unread_bookmarks)

    def test_unread_returns_only_user_owned_bookmarks(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)
        self.setup_bookmark(unread=True, user=other_user)

        response = self.client.get(
            reverse("linkding:feeds.unread", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<item>", count=0)

    def test_shared_returns_404_for_unknown_feed_token(self):
        response = self.client.get(reverse("linkding:feeds.shared", args=["foo"]))

        self.assertEqual(response.status_code, 404)

    def test_shared_metadata(self):
        feed_url = reverse("linkding:feeds.shared", args=[self.token.key])
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Shared bookmarks</title>")
        self.assertContains(response, "<description>All shared bookmarks</description>")
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_shared_returns_shared_bookmarks_only(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=False)

        self.setup_bookmark()
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=True, user=user2)

        shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
        ]

        response = self.client.get(
            reverse("linkding:feeds.shared", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, shared_bookmarks)

    def test_shared_user_parameter(self):
        user1 = self.setup_user(enable_sharing=True)
        user2 = self.setup_user(enable_sharing=True)

        user1_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user1),
        ]
        user2_bookmarks = [self.setup_bookmark(shared=True, user=user2)]

        feed_url = reverse("linkding:feeds.shared", args=[self.token.key])

        # without user parameter
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user1_bookmarks + user2_bookmarks)

        # with user parameter
        response = self.client.get(feed_url + f"?user={user1.username}")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user1_bookmarks)

        response = self.client.get(feed_url + f"?user={user2.username}")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user2_bookmarks)

        # with unknown user
        response = self.client.get(feed_url + "?user=unknown")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, [])

    def test_public_shared_does_not_require_auth(self):
        response = self.client.get(reverse("linkding:feeds.public_shared"))

        self.assertEqual(response.status_code, 200)

    def test_public_shared_metadata(self):
        feed_url = reverse("linkding:feeds.public_shared")
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "<title>Public shared bookmarks</title>")
        self.assertContains(
            response, "<description>All public shared bookmarks</description>"
        )
        self.assertContains(response, f"<link>http://testserver{feed_url}</link>")
        self.assertContains(
            response, f'<atom:link href="http://testserver{feed_url}" rel="self"/>'
        )

    def test_public_shared_returns_publicly_shared_bookmarks_only(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True)
        user3 = self.setup_user(enable_sharing=False)

        self.setup_bookmark()
        self.setup_bookmark(shared=False, user=user1)
        self.setup_bookmark(shared=False, user=user2)
        self.setup_bookmark(shared=True, user=user2)
        self.setup_bookmark(shared=True, user=user3)

        public_shared_bookmarks = [
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
            self.setup_bookmark(shared=True, user=user1, description="test"),
        ]

        response = self.client.get(reverse("linkding:feeds.public_shared"))
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, public_shared_bookmarks)

    def test_public_shared_user_parameter(self):
        user1 = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        user2 = self.setup_user(enable_sharing=True, enable_public_sharing=True)

        user1_bookmarks = [
            self.setup_bookmark(shared=True, user=user1),
            self.setup_bookmark(shared=True, user=user1),
        ]
        user2_bookmarks = [self.setup_bookmark(shared=True, user=user2)]

        feed_url = reverse("linkding:feeds.public_shared")

        # without user parameter
        response = self.client.get(feed_url)
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user1_bookmarks + user2_bookmarks)

        # with user parameter
        response = self.client.get(feed_url + f"?user={user1.username}")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user1_bookmarks)

        response = self.client.get(feed_url + f"?user={user2.username}")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, user2_bookmarks)

        # with unknown user
        response = self.client.get(feed_url + "?user=unknown")
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, [])

    def test_with_query(self):
        tag1 = self.setup_tag()
        bookmark1 = self.setup_bookmark()
        bookmark2 = self.setup_bookmark(tags=[tag1])
        bookmark3 = self.setup_bookmark(tags=[tag1])

        self.setup_bookmark()
        self.setup_bookmark()
        self.setup_bookmark()

        feed_url = reverse("linkding:feeds.all", args=[self.token.key])

        url = feed_url + f"?q={bookmark1.title}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, f"<guid>{bookmark1.url}</guid>", count=1)

        url = feed_url + "?q=" + urllib.parse.quote("#" + tag1.name)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)
        self.assertContains(response, f"<guid>{bookmark2.url}</guid>", count=1)
        self.assertContains(response, f"<guid>{bookmark3.url}</guid>", count=1)

        url = feed_url + "?q=" + urllib.parse.quote(f"#{tag1.name} {bookmark2.title}")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, f"<guid>{bookmark2.url}</guid>", count=1)

    def test_unread_parameter(self):
        self.setup_bookmark(unread=True)
        self.setup_bookmark(unread=True)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)
        self.setup_bookmark(unread=False)

        # without unread parameter
        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=6)

        # with unread=yes
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?unread=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)

        # with unread=no
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?unread=no"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=4)

    def test_shared_parameter(self):
        self.setup_bookmark(shared=True)
        self.setup_bookmark(shared=True)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)
        self.setup_bookmark(shared=False)

        # without shared parameter
        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=6)

        # with shared=yes
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?shared=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=2)

        # with shared=no
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?shared=no"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=4)

    def test_with_tags(self):
        bookmarks = [
            self.setup_bookmark(description="test description"),
            self.setup_bookmark(
                description="test description",
                tags=[self.setup_tag(), self.setup_tag()],
            ),
        ]

        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, bookmarks)

    def test_with_limit(self):
        self.setup_numbered_bookmarks(200)

        # without limit - defaults to 100
        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=100)

        # with increased limit
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?limit=200"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=200)

        # with decreased limit
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?limit=5"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=5)

    @unittest.skipIf(
        settings.LD_DB_ENGINE == "postgres",
        "Postgres does not allow NUL in text columns",
    )
    def test_strip_control_characters(self):
        self.setup_bookmark(
            title="test\n\r\t\0\x08title", description="test\n\r\t\0\x08description"
        )
        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<item>", count=1)
        self.assertContains(response, "<title>test\n\r\ttitle</title>", count=1)
        self.assertContains(
            response, "<description>test\n\r\tdescription</description>", count=1
        )

    def test_sanitize_with_none_text(self):
        self.assertEqual("", sanitize(None))

    def test_with_bundle(self):
        tag1 = self.setup_tag()
        visible_bookmarks = [
            self.setup_bookmark(tags=[tag1]),
            self.setup_bookmark(tags=[tag1]),
        ]

        self.setup_bookmark()
        self.setup_bookmark()

        bundle = self.setup_bundle(all_tags=tag1.name)

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key])
            + f"?bundle={bundle.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFeedItems(response, visible_bookmarks)

    def test_with_bundle_not_owned_by_user(self):
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        other_bundle = self.setup_bundle(user=other_user, search="test")

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key])
            + f"?bundle={other_bundle.id}"
        )
        self.assertEqual(response.status_code, 404)

    def test_with_invalid_bundle_id(self):
        self.setup_bookmark(title="test bookmark")

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?bundle=999999"
        )
        self.assertEqual(response.status_code, 404)

    def test_with_non_numeric_bundle_id(self):
        self.setup_bookmark(title="test bookmark")

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?bundle=invalid"
        )
        self.assertEqual(response.status_code, 404)

    def test_all_with_notes_parameter_yes(self):
        self.setup_bookmark(
            title="Bookmark with notes",
            description="Test description",
            notes="These are some test notes",
        )
        self.setup_bookmark(
            title="Bookmark without notes", description="Another description"
        )

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Bookmark with notes should have notes appended
        self.assertContains(
            response,
            "<description>Test description\n\nNotes:\nThese are some test notes</description>",
            count=1,
        )
        # Bookmark without notes should have description as-is
        self.assertContains(
            response, "<description>Another description</description>", count=1
        )

    def test_all_without_notes_parameter(self):
        self.setup_bookmark(
            title="Bookmark with notes",
            description="Test description",
            notes="These are some test notes",
        )

        response = self.client.get(reverse("linkding:feeds.all", args=[self.token.key]))
        self.assertEqual(response.status_code, 200)

        # Notes should not appear
        self.assertNotContains(response, "These are some test notes")
        self.assertContains(
            response, "<description>Test description</description>", count=1
        )

    def test_all_with_notes_parameter_invalid_value(self):
        self.setup_bookmark(
            title="Bookmark with notes",
            description="Test description",
            notes="These are some test notes",
        )

        # Test various invalid values
        for value in ["true", "1", "Yes", "YES", ""]:
            response = self.client.get(
                reverse("linkding:feeds.all", args=[self.token.key])
                + f"?include_notes={value}"
            )
            self.assertEqual(response.status_code, 200)
            # Notes should not appear with invalid values
            self.assertNotContains(response, "These are some test notes")

    def test_all_with_empty_notes(self):
        self.setup_bookmark(
            title="Bookmark with empty notes", description="Test description", notes=""
        )

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Should not add spurious "Notes:" header
        self.assertContains(
            response, "<description>Test description</description>", count=1
        )
        self.assertNotContains(response, "Notes:")

    def test_all_notes_only_when_description_empty(self):
        self.setup_bookmark(
            title="Bookmark with notes only",
            description="",
            notes="Only notes, no description",
        )

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Should render notes without description prefix
        self.assertContains(
            response,
            "<description>Notes:\nOnly notes, no description</description>",
            count=1,
        )

    def test_all_notes_sanitization(self):
        self.setup_bookmark(
            title="Bookmark with control chars",
            description="Description",
            notes="Notes with\nnewline\ttab\x08backspace\x00null",
        )

        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Newlines and tabs should be preserved, other control chars removed
        self.assertContains(response, "Notes with\nnewline\ttab")
        self.assertNotContains(response, "\x08")
        self.assertNotContains(response, "\x00")

    def test_unread_with_notes_parameter_yes(self):
        self.setup_bookmark(
            title="Unread with notes",
            description="Test description",
            notes="Unread notes",
            unread=True,
        )
        self.setup_bookmark(
            title="Unread without notes",
            description="Another description",
            unread=True,
        )

        response = self.client.get(
            reverse("linkding:feeds.unread", args=[self.token.key])
            + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Bookmark with notes should have notes appended
        self.assertContains(
            response,
            "<description>Test description\n\nNotes:\nUnread notes</description>",
            count=1,
        )
        # Bookmark without notes should have description as-is
        self.assertContains(
            response, "<description>Another description</description>", count=1
        )

    def test_unread_without_notes_parameter(self):
        self.setup_bookmark(
            title="Unread with notes",
            description="Test description",
            notes="Unread notes",
            unread=True,
        )

        response = self.client.get(
            reverse("linkding:feeds.unread", args=[self.token.key])
        )
        self.assertEqual(response.status_code, 200)

        # Notes should not appear
        self.assertNotContains(response, "Unread notes")
        self.assertContains(
            response, "<description>Test description</description>", count=1
        )

    def test_shared_ignores_notes_parameter(self):
        user = self.setup_user(enable_sharing=True)
        self.setup_bookmark(
            title="Shared with notes",
            description="Shared description",
            notes="Private notes that should not appear",
            shared=True,
            user=user,
        )

        response = self.client.get(
            reverse("linkding:feeds.shared", args=[self.token.key])
            + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Notes should never appear in shared feed
        self.assertNotContains(response, "Private notes that should not appear")
        self.assertContains(
            response, "<description>Shared description</description>", count=1
        )

    def test_public_shared_ignores_notes_parameter(self):
        user = self.setup_user(enable_sharing=True, enable_public_sharing=True)
        self.setup_bookmark(
            title="Public shared with notes",
            description="Public description",
            notes="Private notes that should not appear",
            shared=True,
            user=user,
        )

        response = self.client.get(
            reverse("linkding:feeds.public_shared") + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)

        # Notes should never appear in public shared feed
        self.assertNotContains(response, "Private notes that should not appear")
        self.assertContains(
            response, "<description>Public description</description>", count=1
        )

    def test_notes_not_leaked_across_users(self):
        # Create another user with their own feed token
        other_user = User.objects.create_user(
            "otheruser", "otheruser@example.com", "password123"
        )
        other_token = FeedToken.objects.get_or_create(user=other_user)[0]

        # Create bookmark for test user with notes
        self.setup_bookmark(
            title="Test user bookmark",
            description="Test description",
            notes="Test user's private notes",
        )

        # Create bookmark for other user with notes
        self.setup_bookmark(
            title="Other user bookmark",
            description="Other description",
            notes="Other user's private notes",
            user=other_user,
        )

        # Test user's feed should only show test user's notes
        response = self.client.get(
            reverse("linkding:feeds.all", args=[self.token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test user's private notes")
        self.assertNotContains(response, "Other user's private notes")

        # Other user's feed should only show other user's notes
        response = self.client.get(
            reverse("linkding:feeds.all", args=[other_token.key]) + "?include_notes=yes"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Other user's private notes")
        self.assertNotContains(response, "Test user's private notes")
