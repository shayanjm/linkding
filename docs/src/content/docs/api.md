---
title: "API"
description: "How to use the REST API of linkding"
---

The application provides a REST API that can be used by 3rd party applications to manage bookmarks.

## Authentication

All requests against the API must be authorized using an authorization token. The application automatically generates an
API token for each user, which can be accessed through the *Settings* page.

The token needs to be passed as `Authorization` header in the HTTP request:

```
Authorization: Token <Token>
```

## Resources

The following resources are available:

### Bookmarks

**List**

```
GET /api/bookmarks/
```

List bookmarks.

Parameters:

- `q` - Filters results using a search phrase using the same logic as through the UI
- `limit` - Limits the max. number of results. Default is `100`.
- `offset` - Index from which to start returning results
- `modified_since` - Filter results to only include bookmarks modified after the specified date (format: ISO 8601, e.g. "2025-01-01T00:00:00Z")
- `added_since` - Filter results to only include bookmarks added after the specified date (format: ISO 8601, e.g. "2025-05-29T00:00:00Z")
- `bundle` - Filter results by bundle id to only include bookmarks matched by a given bundle

Example response:

```json
{
  "count": 123,
  "next": "http://127.0.0.1:8000/api/bookmarks/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 1,
      "url": "https://example.com",
      "title": "Example title",
      "description": "Example description",
      "notes": "Example notes",
      "web_archive_snapshot_url": "https://web.archive.org/web/20200926094623/https://example.com",
      "favicon_url": "http://127.0.0.1:8000/static/https_example_com.png",
      "preview_image_url": "http://127.0.0.1:8000/static/0ac5c53db923727765216a3a58e70522.jpg",
      "is_archived": false,
      "unread": false,
      "shared": false,
      "tag_names": [
        "tag1",
        "tag2"
      ],
      "date_added": "2020-09-26T09:46:23.006313Z",
      "date_modified": "2020-09-26T16:01:14.275335Z"
    },
    ...
  ]
}
```

**List Archived**

```
GET /api/bookmarks/archived/
```

List archived bookmarks.

Parameters and response are the same as for the regular list endpoint.

**Retrieve**

```
GET /api/bookmarks/<id>/
```

Retrieves a single bookmark by ID.

**Check**

```
GET /api/bookmarks/check/?url=https%3A%2F%2Fexample.com
```

Allows to check if a URL is already bookmarked. If the URL is already bookmarked, the `bookmark` property in the
response holds the bookmark data, otherwise it is `null`.

Also returns a `metadata` property that contains metadata scraped from the website. Finally, the `auto_tags` property
contains the tag names that would be automatically added when creating a bookmark for that URL.

Example response:

```json
{
  "bookmark": {
    "id": 1,
    "url": "https://example.com",
    "title": "Example title",
    "description": "Example description",
    ...
  },
  "metadata": {
    "title": "Scraped website title",
    "description": "Scraped website description",
    ...
  },
  "auto_tags": [
    "tag1",
    "tag2"
  ]
}
```

**Create**

```
POST /api/bookmarks/
```

Creates a new bookmark. Tags are simply assigned using their names. Including
`is_archived: true` saves a bookmark directly to the archive.

If the provided URL is already bookmarked, this silently updates the existing bookmark instead of creating a new one. If
you are implementing a user interface, consider notifying users about this behavior. You can use the `/check` endpoint
to check if a URL is already bookmarked and at the same time get the existing bookmark data. This behavior may change in
the future to return an error instead.

If the title and description are not provided or empty, the application automatically tries to scrape them from the
bookmarked website. This behavior can be disabled by adding the `disable_scraping` query parameter to the API request.

Example payload:

```json
{
  "url": "https://example.com",
  "title": "Example title",
  "description": "Example description",
  "notes": "Example notes",
  "is_archived": false,
  "unread": false,
  "shared": false,
  "tag_names": [
    "tag1",
    "tag2"
  ]
}
```

**Update**

```
PUT /api/bookmarks/<id>/
PATCH /api/bookmarks/<id>/
```

Updates a bookmark.
When using `PUT`, at least all required fields must be provided (currently only `url`).
When using `PATCH`, only the fields that should be updated need to be provided.
Regardless which method is used, any field that is not provided is not modified.
Tags are simply assigned using their names.

Note that [auto tagging](/auto-tagging) rules are applied on every update: tags from
matching rules are merged into `tag_names`, even if the request does not include that field.

If the provided URL is already bookmarked this returns an error.

Example payload:

```json
{
  "url": "https://example.com",
  "title": "Example title",
  "description": "Example description",
  "tag_names": [
    "tag1",
    "tag2"
  ]
}
```

**Archive**

```
POST /api/bookmarks/<id>/archive/
```

Archives a bookmark.

**Unarchive**

```
POST /api/bookmarks/<id>/unarchive/
```

Unarchives a bookmark.

**Delete**

```
DELETE /api/bookmarks/<id>/
```

Deletes a bookmark by ID.

### Bookmark Assets

**List**

```
GET /api/bookmarks/<bookmark_id>/assets/
```

List assets for a specific bookmark.

Example response:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "bookmark": 1,
      "asset_type": "snapshot",
      "date_created": "2023-10-01T12:00:00Z",
      "content_type": "text/html",
      "display_name": "HTML snapshot from 10/01/2023",
      "status": "complete"
    },
    {
      "id": 2,
      "bookmark": 1,
      "asset_type": "upload",
      "date_created": "2023-10-01T12:05:00Z",
      "content_type": "image/png",
      "display_name": "example.png",
      "status": "complete"
    }
  ]
}
```

**Retrieve**

```
GET /api/bookmarks/<bookmark_id>/assets/<id>/
```

Retrieves a single asset by ID for a specific bookmark.

**Download**

```
GET /api/bookmarks/<bookmark_id>/assets/<id>/download/
```

Downloads the asset file.

**Upload**

```
POST /api/bookmarks/<bookmark_id>/assets/upload/
```

Uploads a new asset for a specific bookmark. The request must be a `multipart/form-data` request with a single part
named `file` containing the file to upload.

Example response:

```json
{
  "id": 3,
  "bookmark": 1,
  "asset_type": "upload",
  "date_created": "2023-10-01T12:10:00Z",
  "content_type": "application/pdf",
  "display_name": "example.pdf",
  "status": "complete"
}
```

**Delete**

```
DELETE /api/bookmarks/<bookmark_id>/assets/<id>/
```

Deletes an asset by ID for a specific bookmark.

### Tags

**List**

```
GET /api/tags/
```

List tags.

Parameters:

- `limit` - Limits the max. number of results. Default is `100`.
- `offset` - Index from which to start returning results

Example response:

```json
{
  "count": 123,
  "next": "http://127.0.0.1:8000/api/tags/?limit=100&offset=100",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "example",
      "date_added": "2020-09-26T09:46:23.006313Z"
    },
    ...
  ]
}
```

**Retrieve**

```
GET /api/tags/<id>/
```

Retrieves a single tag by ID.

**Create**

```
POST /api/tags/
```

Creates a new tag.

Example payload:

```json
{
  "name": "example"
}
```

**Delete**

```
DELETE /api/tags/<id>/
```

Deletes a tag by ID.

### Bundles

**List**

```
GET /api/bundles/
```

List bundles.

Parameters:

- `limit` - Limits the max. number of results. Default is `100`.
- `offset` - Index from which to start returning results

Example response:

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Work Resources",
      "search": "productivity tools",
      "any_tags": "work productivity",
      "all_tags": "",
      "excluded_tags": "personal",
      "order": 0,
      "date_created": "2020-09-26T09:46:23.006313Z",
      "date_modified": "2020-09-26T16:01:14.275335Z"
    },
    {
      "id": 2,
      "name": "Tech Articles",
      "search": "",
      "any_tags": "programming development",
      "all_tags": "",
      "excluded_tags": "outdated",
      "order": 1,
      "date_created": "2020-09-27T10:15:30.123456Z",
      "date_modified": "2020-09-27T10:15:30.123456Z"
    },
    ...
  ]
}
```

**Retrieve**

```
GET /api/bundles/<id>/
```

Retrieves a single bundle by ID.

**Create**

```
POST /api/bundles/
```

Creates a new bundle. If no `order` is specified, the bundle will be automatically assigned the next available order position.

Example payload:

```json
{
  "name": "My Bundle",
  "search": "search terms",
  "any_tags": "tag1 tag2",
  "all_tags": "required-tag",
  "excluded_tags": "excluded-tag",
  "order": 5
}
```

**Update**

```
PUT /api/bundles/<id>/
PATCH /api/bundles/<id>/
```

Updates a bundle.
When using `PUT`, all fields except read-only ones should be provided.
When using `PATCH`, only the fields that should be updated need to be provided.

Example payload:

```json
{
  "name": "Updated Bundle Name",
  "search": "updated search terms",
  "any_tags": "new-tag1 new-tag2",
  "order": 10
}
```

**Delete**

```
DELETE /api/bundles/<id>/
```

Deletes a bundle by ID.

### User

**Profile**

```
GET /api/user/profile/
```

User preferences.

Example response:

```json
{
  "theme": "auto",
  "bookmark_date_display": "relative",
  "bookmark_link_target": "_blank",
  "web_archive_integration": "enabled",
  "tag_search": "lax",
  "enable_sharing": true,
  "enable_public_sharing": true,
  "enable_favicons": false,
  "display_url": false,
  "permanent_notes": false,
  "search_preferences": {
    "sort": "title_asc",
    "shared": "off",
    "unread": "off"
  }
}
```

## RSS Feeds

linkding provides RSS feeds for bookmarks, which are authenticated using feed tokens. Each user has a unique feed token that can be accessed through the *Settings* page.

### Available Feeds

**All Bookmarks Feed**

```
GET /feeds/<feed_token>/all
```

Returns all unarchived bookmarks for the authenticated user.

**Unread Bookmarks Feed**

```
GET /feeds/<feed_token>/unread
```

Returns all unread, unarchived bookmarks for the authenticated user.

**Shared Bookmarks Feed**

```
GET /feeds/<feed_token>/shared
```

Returns all shared bookmarks visible to the authenticated user.

**Public Shared Bookmarks Feed**

```
GET /feeds/shared
```

Returns all public shared bookmarks. Does not require authentication.

### Query Parameters

All feeds support the following query parameters:

- `q` - Filters results using a search phrase using the same logic as through the UI
- `limit` - Limits the max. number of results. Default is `100`.
- `user` - Filters shared bookmarks by username (shared feeds only)
- `bundle` - Filter results by bundle id to only include bookmarks matched by a given bundle
- `unread` - Filter by unread status: `yes` or `no`
- `shared` - Filter by shared status: `yes` or `no`

#### Including Notes (All and Unread Feeds Only)

- `include_notes` - Set to exactly `yes` to include bookmark notes in feed descriptions

When `include_notes=yes` is specified on the All or Unread feeds:
- Notes are appended to the bookmark description in the format: `<description>\n\nNotes:\n<notes>`
- If the description is empty, only the notes are shown: `Notes:\n<notes>`
- Notes are sanitized as plain text for RSS compatibility
- Empty notes do not introduce spurious content

**Important:** The `include_notes` parameter is ignored on Shared and Public Shared feeds. Private notes are never exposed in shared feeds, even when this parameter is supplied.

Example:

```
GET /feeds/<feed_token>/all?include_notes=yes
```

