# km-cli command matrix

## auth

- `km-cli auth init`
- `km-cli auth login [--login-url URL] [--state-path FILE] [--user-data-dir DIR]`
- `km-cli auth token --json`

## doc

- Create doc (markdown, recommended): `km-cli doc create --parent-id ID --title TITLE [--markdown TEXT] [--markdown-file FILE] --json`
- Create doc (legacy plain text): `km-cli doc create --parent-id ID --title TITLE [--content TEXT] [--content-file FILE] --json`
- Constraint: `--content*` and `--markdown*` cannot be used together.
- Read content: `km-cli doc get-content --content-id ID [--format markdown|json] [--output FILE]`

## comment

- Full comment summary: `km-cli comment get --content-id ID [--offset N] [--limit N] --json`
- Discussion list: `km-cli comment list --content-id ID [--page-no N] [--page-size N] --json`
- Add page comment: `km-cli comment add --content-id ID --text TEXT --json`
- Reply discussion: `km-cli comment reply --content-id ID --discussion-id ID [--quote-id ID] --text TEXT --json`

## edit

## expected key output fields

- `doc create`: `contentId`, `url`
- `comment add`: `commentId`
- `comment reply`: `replyId`, `discussionId`, `quoteId`
