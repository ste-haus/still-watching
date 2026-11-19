# still-watching

An "Are you still watching?" prompt for Jellyfin, driven by the official [Webhook plugin](https://github.com/jellyfin/jellyfin-plugin-webhook).

Forked from [joshjryan/sleep-timer](https://github.com/joshjryan/sleep-timer).

## How it works

still-watching follows each user on each device separately and counts runs of episodes.

- **An episode counts once it has played for a minute** (`START_DELAY_SECONDS`). Stopping it, or starting something else, inside that minute means it never counted, so skipping through episodes does not build up a run.
- **The next episode continues the run if it starts within 10 minutes of the previous one ending** (`RUN_GAP_MINUTES`). The end comes from the `PlaybackStop` event. If no stop arrives, for example because the client disappeared, the previous episode is assumed to have ended at its start plus its running time.
- **A different series, or any movie, starts a new run.**
- **Resuming an episode that already counted does not count it again**, whether it was paused or stopped and restarted.
- **When an episode would make the run longer than 4** (`RUN_LENGTH`), once that episode has played for the start delay, still-watching shows "Are you still watching?" on the client and then pauses it (`JELLYFIN_STOP_ACTION`). That episode becomes the first of a new run, so resuming it gives another full run before the next prompt.

With the defaults, four back-to-back episodes play through, and the fifth pauses a minute in.

Run counts live in memory, so restarting the container resets them.

## Setup

1. Run the container (see below).
2. Install the Jellyfin Webhook plugin.
3. Add a **Generic** destination:
   - **Webhook URL:** `http://<still-watching-address>:5553/webhook`
   - **Notification types:** `Playback Start` and `Playback Stop`
   - **Item types:** Episodes and Movies (movies reset the run)
   - **Users:** the users to apply it to
   - **Send All Properties (ignores template):** checked
4. Create an API key in Jellyfin (Dashboard → API Keys) for `JELLYFIN_API_TOKEN`.

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `JELLYFIN_API_URL` | yes | | Jellyfin server address, e.g. `http://jellyfin:8096` |
| `JELLYFIN_API_TOKEN` | yes | | Jellyfin API key, sent as `Authorization: MediaBrowser Token="…"` |
| `RUN_LENGTH` | no | `4` | Episodes in a row allowed before asking |
| `RUN_GAP_MINUTES` | no | `10` | Longest break between one episode ending and the next starting that still continues a run |
| `START_DELAY_SECONDS` | no | `60` | How long an episode must play before it counts |
| `JELLYFIN_MESSAGE` | no | `Are you still watching?` | Message shown on the client |
| `JELLYFIN_STOP_ACTION` | no | `PAUSE` | `PAUSE`, or `STOP` to stop playback and return the client to its home screen |

## Docker Compose

```yaml
services:
  still-watching:
    image: ghcr.io/ste-haus/still-watching:latest
    container_name: still-watching
    ports:
      - "5553:5553"
    environment:
      JELLYFIN_API_URL: "http://jellyfin:8096"
      JELLYFIN_API_TOKEN: "<api key>"
      RUN_LENGTH: 4
      RUN_GAP_MINUTES: 10
      START_DELAY_SECONDS: 60
      JELLYFIN_STOP_ACTION: "PAUSE"
    restart: unless-stopped
```

The image runs a single gunicorn worker on purpose: run counts are held in that process's memory.

## Development

```bash
make install   # runtime and test dependencies
make test      # pytest
make publish   # build and push ghcr.io/ste-haus/still-watching:<VERSION> and :latest
```

## Releases

Every push to `main` runs the tests, then builds and pushes `ghcr.io/ste-haus/still-watching` tagged with the version in `VERSION`, its `major.minor` series, `latest`, and `sha-<commit>`, and then tags the commit `v<VERSION>`. The build fails if that tag already exists, so bump `VERSION` in every pull request.
