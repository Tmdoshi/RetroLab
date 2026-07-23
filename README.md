# Retro Lab — Cloud Server Project

**Student Name:** Tanishk Doshi
**Student Number:** [insert student number]
**Unit:** ICT171 — Introduction to Server Environments and Architectures
**Live site:** https://retrolabs.online
**IP address (Elastic IP):** 3.78.92.231
**GitHub repository:** https://github.com/Tmdoshi/RetroLab
**Video walkthrough:** [insert link once recorded]

---

## 1. Project Overview

Retro Lab is a marketplace web application for buying and selling retro gaming hardware — consoles, handhelds, computers, and accessories. It's built with **Flask** (Python) on the backend, **SQLite** for data storage, and is served in production through **Apache** using **mod_wsgi**, with a manually configured SSL/TLS certificate from Let's Encrypt.

This document covers how the server was built from a bare EC2 instance through to a fully secured, publicly accessible site, and explains the reasoning behind each configuration choice, not just the commands used.

---

## 2. Infrastructure — EC2 Instance

The application is hosted on an AWS EC2 instance running Ubuntu, configured manually via SSH (no pre-built AMIs or bundled server images were used, in line with the assignment's IaaS requirement).

**Instance details:**
- AMI: Ubuntu (via EC2)
- Instance type: t2.micro / t3.micro
- Region: eu-central-1

**Security Group inbound rules:**

| Port | Protocol | Purpose |
|------|----------|---------|
| 22   | TCP      | SSH access for server administration |
| 80   | TCP      | HTTP traffic (redirects to HTTPS) |
| 443  | TCP      | HTTPS traffic (encrypted site access) |

An **Elastic IP** (3.78.92.231) was allocated and associated with the instance. This matters because a normal EC2 public IP changes every time the instance is stopped and restarted — an Elastic IP stays fixed, which is essential once DNS is pointing a domain name at it. Without it, every reboot would break the domain's A record.

📸 *[Insert screenshot: EC2 console showing instance running + Elastic IP attached]*
📸 *[Insert screenshot: Security Group inbound rules]*

---

## 3. Domain Registration & DNS

The domain **retrolabs.online** was registered through GoDaddy.

An **A record** was added in GoDaddy's DNS management panel:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | @ | 3.78.92.231 | Default |
| A | www | 3.78.92.231 | Default |

DNS is a completely separate system from the web server itself — the A record only tells the internet "this domain name maps to this IP address." It doesn't know or care what software is actually running on that server; that's Apache's job. Propagation was verified using [dnschecker.org](https://dnschecker.org), confirming the domain resolved correctly to the Elastic IP from multiple global locations before moving on to server configuration.

📸 *[Insert screenshot: DNS panel showing the A record pointed at the Elastic IP]*
📸 *[Insert screenshot: dnschecker.org showing green checkmarks / resolved IP]*

---

## 4. Server Setup — Apache + Flask (via mod_wsgi)

### 4.1 Package Installation

After SSH-ing into the instance, the system was updated and the required packages installed:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y apache2 python3-pip python3-venv libapache2-mod-wsgi-py3 sqlite3 git
```

📸 *[Insert screenshot: terminal output of successful install]*

### 4.2 Application Setup

The application directory was created, ownership assigned, and a Python virtual environment set up to isolate the project's dependencies from the system's Python installation:

```bash
sudo mkdir -p /var/www/retrolab
sudo chown -R ubuntu:www-data /var/www/retrolab
cd /var/www/retrolab
python3 -m venv venv
source venv/bin/activate
pip install flask
```

The application code was pulled directly from GitHub onto the server:

```bash
git clone https://github.com/Tmdoshi/RetroLab.git temp-clone
cp -r temp-clone/. .
rm -rf temp-clone
```

(A temporary clone folder was used here because the `venv` directory already existed in `/var/www/retrolab`, and `git clone` refuses to clone directly into a non-empty directory.)

The SQLite database was then initialised using the project's setup script, which creates the `listings` table and seeds it with sample marketplace data:

```bash
python3 init_db.py
```

Before wiring up Apache, the app was tested directly with Flask's built-in development server to confirm it worked in isolation:

```bash
flask run --host=0.0.0.0
```

and verified from a second terminal session with:

```bash
curl localhost:5000
```

which returned the expected HTML output of the homepage.

📸 *[Insert screenshot: directory listing showing app.py, templates/, retrolab.db]*
📸 *[Insert screenshot: flask run output + curl output confirming the app works before Apache]*

### 4.3 WSGI Entry Point

Apache does not natively understand Python — it only knows how to serve static files and hand requests off to modules it's configured with. **mod_wsgi** is the bridge that lets Apache launch and communicate with a Python web application. The WSGI entry point file tells mod_wsgi exactly which Python object represents the application:

`/var/www/retrolab/retrolab.wsgi`:
```python
import sys
sys.path.insert(0, '/var/www/retrolab')

from app import app as application
```

### 4.4 Apache Configuration

Apache's WSGI daemon process was defined in its own global configuration file rather than inside the virtual host itself:

`/etc/apache2/conf-available/retrolab-wsgi.conf`:
```apache
WSGIDaemonProcess retrolab user=www-data group=www-data threads=5 python-home=/var/www/retrolab/venv
```

```bash
sudo a2enconf retrolab-wsgi.conf
```

**Why this matters (a lesson learned the hard way):** when Certbot later configures SSL, it duplicates the virtual host block to create a second one for port 443. If `WSGIDaemonProcess` is defined inside the virtual host itself, Certbot's copy creates a second definition of the *same* named daemon process, which Apache refuses to start — the process name has to be unique server-wide. Defining it once in a global config file, and only *referencing* it (`WSGIProcessGroup retrolab`) inside each virtual host, avoids this conflict entirely. This tripped up the initial SSL setup and is worth flagging for anyone following this guide.

The virtual host itself was configured at `/etc/apache2/sites-available/retrolab.conf`:

```apache
<VirtualHost *:80>
    ServerName retrolabs.online
    ServerAlias www.retrolabs.online

    WSGIScriptAlias / /var/www/retrolab/retrolab.wsgi

    <Directory /var/www/retrolab>
        WSGIProcessGroup retrolab
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>

    Alias /static /var/www/retrolab/static
    <Directory /var/www/retrolab/static>
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/retrolab_error.log
    CustomLog ${APACHE_LOG_DIR}/retrolab_access.log combined
</VirtualHost>
```

File and directory permissions were set so that the `www-data` user (which Apache runs as) can read the application and write to the SQLite database file:

```bash
sudo chown -R www-data:www-data /var/www/retrolab
sudo chmod 664 /var/www/retrolab/retrolab.db
sudo chmod 775 /var/www/retrolab
```

The site was enabled and the default Apache placeholder site disabled:

```bash
sudo a2ensite retrolab.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

**A second issue encountered here:** the application initially crashed with `sqlite3.OperationalError: unable to open database file` once running under Apache, despite working fine under the Flask dev server. The cause was that `app.py` referenced the database using a **relative path** (`"retrolab.db"`), which resolved correctly when Flask was run manually from inside the project folder, but resolved to nothing meaningful under Apache/WSGI's different working directory. The fix was to use an absolute path instead, resolved relative to the script's own location:

```python
import os
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retrolab.db")
```

📸 *[Insert screenshot: apache2ctl configtest showing "Syntax OK"]*
📸 *[Insert screenshot: visiting http://retrolabs.online showing the site live over plain HTTP]*

---

## 5. SSL/TLS with Certbot

SSL was configured manually using Certbot's Apache plugin, which handles the ACME protocol exchange with Let's Encrypt automatically:

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d retrolabs.online -d www.retrolabs.online
```

Certbot proves domain ownership to Let's Encrypt via the ACME protocol (essentially demonstrating control over the domain by responding to a challenge Apache serves on the domain's behalf), then issues a certificate valid for 90 days. A systemd timer is installed automatically by Certbot to renew the certificate in the background before it expires, so it never needs to be reissued manually under normal circumstances.

Certbot also configured an automatic HTTP → HTTPS redirect, confirmed with:

```bash
curl -I http://retrolabs.online
```
```
HTTP/1.1 301 Moved Permanently
Location: https://retrolabs.online/
```

Renewal was tested with a dry run (this simulates a renewal without actually reissuing anything, purely to confirm the automated timer/configuration is functioning):

```bash
sudo certbot renew --dry-run
```
```
Congratulations, all simulated renewals succeeded:
  /etc/letsencrypt/live/retrolabs.online/fullchain.pem (success)
```

The deployment was independently verified using the [Qualys SSL Labs](https://www.ssllabs.com/ssltest/) server test, which returned an **A rating**, with full marks across Certificate, Protocol Support, Key Exchange, and Cipher Strength, and confirmed support for TLS 1.3.

📸 *[Insert screenshot: Certbot success output]*
📸 *[Insert screenshot: browser padlock icon on https://retrolabs.online]*
📸 *[Insert screenshot: SSL Labs A rating result]*
📸 *[Insert screenshot: certbot renew --dry-run success output]*

---

## 6. Script Component — Database Validation

`scripts/validate_listings.py` is a commented Python script that checks the live SQLite database for data-quality issues:

- Duplicate listing titles
- Non-positive or missing prices
- Missing required fields (category, seller name)

It queries the database directly and prints a plain-text report, so its output can be independently re-verified at any time simply by running it again against the live `retrolab.db`:

```bash
python3 scripts/validate_listings.py
```

```
No duplicate listing titles found.
All listings have valid (positive) prices.
All listings have required fields populated.
Checked 5 listings. 0 issue(s) found.
```

📸 *[Insert screenshot: script output above]*

---

## 7. Repository Structure

```
retro-lab/
├── README.md
├── app.py
├── init_db.py
├── requirements.txt
├── retrolab.wsgi
├── .gitignore
├── templates/
│   ├── index.html
│   ├── listing.html
│   └── add.html
├── static/
│   └── style.css
└── scripts/
    └── validate_listings.py
```

---

## 8. References

- Flask documentation — https://flask.palletsprojects.com/
- Apache mod_wsgi documentation — https://modwsgi.readthedocs.io/
- Let's Encrypt / Certbot documentation — https://certbot.eff.org/
- DNS Checker — https://dnschecker.org
- Qualys SSL Labs Server Test — https://www.ssllabs.com/ssltest/
