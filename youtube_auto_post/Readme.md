# Installation and Configuration Guide for YouTube Auto Post Odoo Addon

This guide provides step-by-step instructions for installing the `youtube_auto_post` Odoo addon, configuring a Google Cloud account to enable the YouTube Data API, creating and downloading the `client_secrets.json` file, and using the addon to automate YouTube video uploads with a scheduler. The addon allows users to upload the `client_secrets.json` file via Odoo’s settings interface and manage video uploads seamlessly.

## Overview

The `youtube_auto_post` addon enables Odoo users to schedule and automate video uploads to YouTube using the YouTube Data API. Key features include:

- Uploading videos stored as Odoo attachments (`ir.attachment`).
- Scheduling uploads via Odoo’s cron job.
- Managing YouTube API credentials (`client_secrets.json`) through a settings interface.
- Handling OAuth 2.0 authentication to generate a `token_youtube_v3.pickle` file for repeated use.

## Prerequisites

- **Odoo Installation**: Odoo 18.
- **Python Environment**: A Python environment with Odoo dependencies installed.
- **Google Cloud Account**: Required for YouTube Data API access. Sign up at Google Cloud Console.
- **Video Files**: Videos must be in supported formats (e.g., MP4, MOV, AVI) and stored as attachments in Odoo.
- **System Requirements**: Write permissions for the Odoo addons directory and a working internet connection.
- **Admin Access**: Access to Odoo’s settings menu (requires `base.group_system` permissions).

## Step 1: Set Up Google Cloud and Create `client_secrets.json`

### 1.1 Create a Google Cloud Project

- Visit the Google Cloud Console.
- Click **New Project** (top dropdown), enter a project name (e.g., `youtubeAutoPost`), and click **Create**.
- Select the project from the top dropdown.

### 1.2 Enable YouTube Data API

- In the Google Cloud Console, go to **APIs & Services** &gt; **Library**.
- Search for **YouTube Data API v3** and click **Enable**. Refer to YouTube Data API Documentation for details.

### 1.3 Create OAuth 2.0 Credentials

- Navigate to **APIs & Services** &gt; **Credentials**.
- Click **Create Credentials** &gt; **OAuth 2.0 Client IDs**.
- Select **Desktop app** as the application type, enter a name (e.g., `YouTube Upload Client`), and click **Create**.
- Download the `client_secrets.json` file by clicking the download icon next to the created client ID. Save it temporarily on your system.

### 1.4 Configure OAuth Consent Screen

- Go to **APIs & Services** &gt; **OAuth consent screen**.
- Select **External** as the user type and click **Create**.
- Fill in required fields:
  - **App name**: `youtubeAutoPost`
  - **User support email**: Your email address.
  - **Developer contact information**: Your email address.
- Under **Scopes**, ensure `https://www.googleapis.com/auth/youtube.upload` is added (it should be automatic after enabling the API).
- Under **Test users**, click **+ Add Users** and add the email address of the Google account you’ll use for YouTube uploads (e.g., your account or the account managing the YouTube channel). This is critical to avoid the "Access blocked" error during authentication.
- Save and set the app to **Testing** mode (or **In production** if you plan to verify it later).

### 1.5 Verify Your YouTube Account (Optional)

- If uploading videos longer than 15 minutes, verify your YouTube account at YouTube Verification using a phone number. This enables uploads up to 12 hours or 256 GB. See YouTube Upload Guidelines.

## Step 2: Install the Odoo Addon

### 2.1 Install Python Dependencies

- In your Odoo Python environment (e.g., virtual environment), install the required libraries:

  ```bash
  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
  ```

### 2.2 Install the Addon

- Copy the `youtube_auto_post` addon folder (provided separately or generated via scaffolding) to your Odoo custom addons directory (e.g., `/path/to/custom/addons/youtube_auto_post`).

- Alternatively, scaffold the module:

  ```bash
  cd /path/to/odoo
  ./odoo-bin scaffold youtube_auto_post /path/to/custom/addons
  ```

  Replace the generated files with the provided addon files (e.g., `models/youtube_upload.py`, `views/youtube_settings_views.xml`, etc.). See Odoo Module Development.

- Create a `static/` folder for the `token_youtube_v3.pickle` file and ensure write permissions:

  ```bash
  mkdir -p /path/to/custom/addons/youtube_auto_post/static
  chmod -R u+w /path/to/custom/addons/youtube_auto_post/static
  ```

### 2.3 Update Odoo Configuration

- Edit your Odoo configuration file (`odoo.conf`) to include the custom addons path:

  ```ini
  [options]
  addons_path = /path/to/odoo/addons,/path/to/custom/addons
  ```

### 2.4 Install the Addon in Odoo

- Start or restart your Odoo server:

  ```bash
  ./odoo-bin -c /path/to/odoo.conf
  ```

- Log in to Odoo, enable **Developer Mode** (Settings &gt; Activate the developer mode).

- Go to **Apps**, click **Update Apps List**, search for **YouTube Video Auto Posting**, and click **Install**. If already installed, click **Upgrade** to apply the latest version (1.1).

## Step 3: Configure the Addon in Odoo

### 3.1 Upload `client_secrets.json`

- Log in as an admin user (with `base.group_system` permissions).
- Go to **Youtube Uploads &gt; YouTube API Settings**.
- In the form, click the **Client Secrets JSON** field and upload the `client_secrets.json` file downloaded from Google Cloud Console.
- Save the record. The file is stored as an `ir.attachment` and will be used for YouTube API authentication.

### 3.2 Authenticate with YouTube

- Go to **YouTube Uploads**.
- Create a new record by clicking **New** and fill in:
  - **Title**: The video’s title for YouTube.
  - **Description**: Optional video description.
  - **Tags**: Comma-separated tags (e.g., `video,odoo,automation`).
  - **Category**: Select a YouTube category (e.g., `People & Blogs`). See YouTube Video Categories.
  - **Privacy Status**: Choose `public`, `private`, or `unlisted`.
  - **Video File**: Attach a video file (MP4, MOV, or AVI).
  - **Schedule Date**: Optional date/time for scheduled uploads.
- Click **Upload Now** to trigger an immediate upload.
- The first time you upload, a browser window will open for OAuth 2.0 authentication:
  - Sign in with the Google account added as a test user in the Google Cloud Console (Step 1.4).
  - Authorize the app to access YouTube.
- Upon successful authentication, the addon generates `token_youtube_v3.pickle` in `youtube_auto_post/static/` (e.g., `/path/to/custom/addons/youtube_auto_post/static/token_youtube_v3.pickle`).

### 3.3 Configure the Scheduler

- The addon includes a cron job that runs every 15 minutes to process uploads with `state=scheduled` and a past-due `schedule_date`.
- To adjust the schedule, go to **Settings &gt; Technical &gt; Automation &gt; Scheduled Actions**, find **YouTube Video Upload**, and modify the **Interval** (e.g., to 1 hour).

## Step 4: Use the Addon

### 4.1 Manual Upload

- In **YouTube Uploads**, create a record, attach a video, and click **Upload Now**.
- Check the **YouTube Video ID** field for the uploaded video’s ID and the **Status** field (should be `uploaded` if successful).
- If the upload fails, the **Error Message** field will show details.

### 4.2 Scheduled Upload

- Set a **Schedule Date** (e.g., 5 minutes from now), click **Schedule Upload**, and wait for the cron job to run.
- Verify the upload by checking the **YouTube Video ID** and **Status**.

### 4.3 View on YouTube

- Use the **YouTube Video ID** to access the video (e.g., `https://www.youtube.com/watch?v=VIDEO_ID`).

## Troubleshooting

### Common Issues

- **"Access blocked: youtubeAutoPost has not completed the Google verification process"**:

  - Ensure the Google account used for authentication is added as a test user in Google Cloud Console under **OAuth consent screen** &gt; **Test users**.

  - Delete `token_youtube_v3.pickle` and retry:

    ```bash
    rm /path/to/custom/addons/youtube_auto_post/static/token_youtube_v3.pickle
    ```

- **No** `.pickle` **File Generated**:

  - Verify `client_secrets.json` is uploaded in **YouTube API Settings** and is valid.

  - Check write permissions for the `static/` folder:

    ```bash
    chmod -R u+w /path/to/custom/addons/youtube_auto_post/static
    ```

- **File Format Errors**: Ensure video files are MP4, MOV, or AVI and not corrupted.

- **Quota Limits**: Each upload uses \~1,600 units of the 10,000-unit daily quota (\~6 uploads/day). Request an increase in Google Cloud Console if needed. See YouTube API Quota.

- **Cron Not Running**: Ensure the Odoo server is running and the **YouTube Video Upload** scheduled action is active in **Settings &gt; Technical &gt; Scheduled Actions**.

### Debugging

- Check Odoo logs for errors:

  ```bash
  ./odoo-bin -c /path/to/odoo.conf --log-level=debug
  ```

- Verify the YouTube Data API is enabled in Google Cloud Console under **APIs & Services** &gt; **Library**.

## Security Notes

- Protect `token_youtube_v3.pickle`:

  ```bash
  chmod 600 /path/to/custom/addons/youtube_auto_post/static/token_youtube_v3.pickle
  ```

- The `client_secrets.json` file is stored as an `ir.attachment`, accessible only to admin users. Ensure only trusted users have `base.group_system` access.

- Do not expose the `static/` folder publicly.

## Additional Notes

- **Video Length**: Videos can be up to 12 hours or 256 GB if your YouTube account is verified at YouTube Verification.
- **Production Use**: For non-test users, submit your app for Google verification in Google Cloud Console under **OAuth consent screen**. See Google API Verification.
- **Customization**: Extend the addon for features like batch uploads or integration with other Odoo modules. Refer to Odoo Module Development.

**Support**: Consult YouTube Data API Documentation or Odoo Community Forums for help.