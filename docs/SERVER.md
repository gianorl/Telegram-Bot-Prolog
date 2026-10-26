# Server (VPS)

Tencent Cloud Lighthouse, Jakarta. Bought 26 Oct 2026, prepaid 12 months ($10.08, renews around $50/year: check Billing Center → Renewal Management is set to manual).

| | |
|---|---|
| Plan | 2 vCPU, 2 GB RAM, 40 GB SSD, 0.5 TB traffic/month |
| OS | Ubuntu 24.04 LTS (x86_64) |
| Login | `ssh prolog` (alias in `~/.ssh/config`, user `ubuntu`, key `~/.ssh/id_prolog_vps`) |
| Emergency door | Tencent console → OrcaTerm / VNC login |

## Hardening (done 26 Oct 2026)

| What | Where | Check |
|---|---|---|
| SSH: key only, no passwords, no root login, 3 tries per connection | `/etc/ssh/sshd_config.d/00-prolog-hardening.conf` (00- wins over Tencent's 50-cloud-init.conf: first value wins) | `sudo sshd -T \| grep -i passwordauth` |
| Firewall: deny all incoming except 22/tcp | `ufw` | `sudo ufw status` |
| fail2ban: 5 failures in 10 min → 1 h ban | `/etc/fail2ban/jail.local` (journalmatch fixed to `ssh.service`; Ubuntu's default `sshd.service` matches nothing) | `sudo fail2ban-client status sshd` |
| Automatic security updates | `unattended-upgrades` (on by default) | `cat /etc/apt/apt.conf.d/20auto-upgrades` |
| Swap 1.9 GB | `/swap.img` (came with the image) | `swapon --show` |

Users: `ubuntu` (me, sudo), `root` and `lighthouse` (Tencent helper) have locked passwords and no SSH keys.

## Rules
- Postgres listens on localhost only. DBeaver connects through an SSH tunnel, never an open 5432.
- `.env` is written by hand on the server, never copied through git.
- Shut down from the console before any operation that forces a shutdown (e.g. key binding).
- Only one bot runs at a time (polling): stop the Mac bot once the server bot is up.

## Prolog on the server (deployed 26 Oct 2026)

```
/home/prolog/app/          git clone of the public repo, owned by Linux user "prolog"
├── venv/                  Python 3.12 (Ubuntu's, patched by auto-updates)
└── .env                   chmod 600, written by hand; token copied with a pipe, never printed
/etc/systemd/system/prolog.service   starts at boot, restarts 10 s after a crash
PostgreSQL 18 (PGDG repo)  role "prolog", databases prolog + prolog_test, localhost only,
                           no password: Linux user prolog = Postgres role prolog (peer auth)
```

| Task | Command (from the Mac) |
|---|---|
| Deploy pushed code | `./scripts/deploy.sh` |
| Add or change a `.env` value (hidden input, restarts the bot) | `./scripts/set-env.sh NAME` |
| Status | `ssh prolog systemctl status prolog` |
| Live logs | `ssh prolog sudo journalctl -u prolog -f` (Ctrl + C to stop) |
| Restart | `ssh prolog sudo systemctl restart prolog` |
| Stop | `ssh prolog sudo systemctl stop prolog` |
| SQL shell | `ssh -t prolog sudo -u prolog psql prolog` |

Data moved from the Mac with `pg_dump -Fc` → `pg_restore` (copy in `backups/prolog-2026-10-26-to-vps.dump`). **The server is now the real data.** The Mac database is a stale copy.

## Backups

```
02:00 WIB  server: prolog-backup.timer → pg_dump → /var/backups/prolog/prolog-YYYY-MM-DD.dump (keeps 14 days)
09:00      Mac: launchd job com.prolog.pull-backups → rsync → ~/Backups/prolog-vps/ (keeps everything)
```

- Server side: `/usr/local/bin/prolog-backup`, `/etc/systemd/system/prolog-backup.{service,timer}`. `Persistent=true` runs a missed backup at boot.
- Check: `ssh prolog systemctl list-timers prolog-backup.timer` and `ssh prolog ls -l /var/backups/prolog`
- Restore test (done 26 Oct 2026, counts matched): restore into a throwaway database, compare counts, drop it.
- Mac side, install once:
  ```bash
  mkdir -p ~/Backups/prolog-vps
  cp scripts/com.prolog.pull-backups.plist ~/Library/LaunchAgents/
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.prolog.pull-backups.plist
  ```
  Remove: `launchctl bootout gui/$(id -u)/com.prolog.pull-backups` and delete the plist. Log: `~/Backups/prolog-vps.log`.
- Copy by hand any time: `rsync -a prolog:/var/backups/prolog/ ~/Backups/prolog-vps/`

Server clock and Postgres are on Asia/Jakarta (Tencent's default was Asia/Shanghai).

## Next
- DBeaver through an SSH tunnel
