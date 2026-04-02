# AWS SSO Auto-login (with Microsoft AD Login)

## Overview

The application runs a headless firefox instance with Selenium, and attempts to login via
Microsoft AD. The login and TOTP credentials need to be configured.

Each time the application runs, it first checks the `~/.aws/sso/cache` directory for a `*.json`
file which has both, an `accessToken` as well as an `expiryAt` key. The file containing both these
keys corresponds to the file storing the SSO session token information. The application checks
the expiry time, and triggers a headless login flow only when:

- The expiry time is less than 10 minutes from now
- The expiry time is in the past
- The JSON file containing the expiry time does not exist

## Setup

### Environment Variables

Create a `.env ` file:

```sh
cp env.template .env
```

Update the `.env` file with your credentials and `aws` CLI path.

### Python Dependencies

Setup a python virtual environment:

```sh
python3 -m venv venv
```

Install dependencies:

```sh
source venv/bin/activate
pip install -r requirements.txt
```

### Add TOTP Method on Microsoft

1. Go to the [Microsoft security info](https://mysignins.microsoft.com/security-info) page
1. Click on `Add sign-in method`
1. Select `Authentitcator app` as the method
1. Select `I want to use a different authentitcator app` on the next screen
1. When the QR code is generated, select `Can't scan image?`
1. Copy the generated manaul entry code, and set it as the TOTP secret of the `.env` file
1. In the next screen, where a generated TOTP is required, run the following to generate one:
   ```
   source venv/bin/activate
   python main.py totp
   ```

Following the steps above should successfully add the sign-in method to your Microsoft account.

### Add AWS Profiles

Configure all roles that you want to access via AWS CLI, in the `~/.aws/config` file. Ensure
that they all share the same SSO session. Here's an example configuration:

```toml
[sso-session common]
sso_start_url = https://<aws-domain>.awsapps.com/start#
sso_region = ap-south-1
sso_registration_scopes = sso:account:access

[profile data-platform-admins]
sso_session = common
sso_account_id = 598765432100
sso_role_name = data-platform-admins
region = ap-south-1
```

Note that the `sso-session` section is required, and the same session (`common` in the example above)
can be re-used across profiles with the `sso_session` configuration key.

### Crontab

Add a `cron` entry according to the output of this command:

```sh
printf "\n*/5 * * * *                $(pwd)/run.sh\n\n"
```

You can update the `cron` expression as required (above runs the script once every 15 minutes).

Add it to the current user's `cron` **(do not use `sudo`)**:

```sh
crontab -e
```

**Note (Macbook Users):** If this is the first `cron` you are scheduling in your system, you may
have to set it up with requisite permissions first. Refer
[this](https://discussions.apple.com/thread/255350091?answerId=259957456022&sortBy=best#259957456022)
answer. Note that the first time the `cronjob` runs, you may be asked for permission to allow
the `python3.xx` program to operate in the background.

## Microsoft Active Directory Checker

As a side-product, this script also supports checking for, and logging into, Microsoft's Active
Directory on the connected network. This is useful if overzealous security configuration of the
network at your workplace requires you to login into your AD every few hours or so. This script
automates that process.

To add this script to `cron`, include the output of this command in your `crontab`:

```sh
printf "\n*/10 * * * *                $(pwd)/run-ad-check.sh\n\n"
```

## Troubleshooting

### Logs

You can run the script directly to see logs:

```sh
./venv/bin/python main.py
```

The `run.sh` script generates logs in the `~/.cache/aws-sso-auto-login.log` file. The file
is overwritten during each execution. If the `~/.cache` folder does not exist, you may have to
create it:

```sh
mkdir -p ~/.cache
```

### Selenium Errors

It is possible that the AWS SSO flow is updated, due to which the Selenium automation begins to
fail. To check if this is the case, set `RENDER_BROWSER=1` in the `.env`, and manually trigger
the script. Remember to revert this back in case you have an active `cron`, as otherwise browser
windows will open out of nowhere all the time!

### Missing Driver

Selenium may raise a `selenium.common.exceptions.NoSuchDriverException` if its unable to find the
firefox binary in the default location. In this case, add the `FIREFOX_BINARY_PATH` environment
variable to the `.env` file.

### Invalid Host Error

You may see an error such as:

```
selenium.common.exceptions.WebDriverException: Message: Invalid Host header localhost:50939
```

This is likely due to a missing entry in `/etc/hosts` for `localhost`. Add it:

```sh
sudo vim /etc/hosts
```

Add the following line:

```
127.0.0.1               localhost
```
