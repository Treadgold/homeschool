# Facebook Login Setup Guide

This guide will help you set up Facebook Login for your LifeLearners homeschool application.

## Prerequisites

1. A Facebook account
2. Facebook Developer Account access

## Step 1: Create a Facebook App

1. Go to [Facebook for Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Choose "Consumer" or "Business" (Consumer is fine for this use case)
4. Fill in the app details:
   - App Name: "LifeLearners Homeschool"
   - App Contact Email: Your email
   - App Purpose: Select appropriate option

## Step 2: Configure Facebook Login

1. In your Facebook app dashboard, click "Add Product"
2. Find "Facebook Login" and click "Set Up"
3. Select "Web" as the platform
4. Enter your Site URL: `http://localhost:8000` (for development)

## Step 3: Configure OAuth Settings

1. Go to Facebook Login → Settings in the left sidebar
2. Under "Valid OAuth Redirect URIs", add:
   - `http://localhost:8000/auth/facebook/callback` (for development)
   - `https://yourdomain.com/auth/facebook/callback` (for production)
3. Save changes

## Step 4: Get Your App Credentials

1. Go to Settings → Basic in your app dashboard
2. Copy your "App ID" and "App Secret"

## Step 5: Configure Environment Variables

Add these environment variables to your system or `.env` file:

```bash
# Facebook OAuth Configuration
FACEBOOK_CLIENT_ID=your_app_id_here
FACEBOOK_CLIENT_SECRET=your_app_secret_here
```

## Step 6: Test the Integration

1. Install the new dependencies: `pip install -r requirements.txt`
2. **Important**: Run the database migration: `alembic upgrade head`
3. Start your application: `uvicorn app.main:app --reload`
4. Check the health endpoint: `curl http://localhost:8000/health` to verify schema status
5. Visit `http://localhost:8000/login` and try the Facebook login button

### Docker Users

If you're using Docker Compose:

1. **Stop your containers**: `docker-compose down`
2. **Build with new dependencies**: `docker-compose build`
3. **Run the migration**: `docker-compose run web alembic upgrade head`
4. **Start the application**: `docker-compose up`

The application will now gracefully handle missing database columns and provide helpful error messages.

## Production Configuration

For production deployment:

1. Add your production domain to Facebook app settings
2. Update the OAuth redirect URI to use HTTPS
3. Set the environment variables on your production server
4. Ensure your SITE_URL environment variable is set correctly

## Security Notes

- Never commit your Facebook App Secret to version control
- Use HTTPS in production
- Regularly rotate your app secret if needed
- Review Facebook's data use policies and ensure compliance

## Troubleshooting

### Common Issues

1. **"Invalid OAuth access token"**: Check that your app secret is correct
2. **"Redirect URI mismatch"**: Ensure the redirect URI in Facebook matches exactly
3. **"App not live"**: Your Facebook app might need to be made live in the app dashboard

### Facebook App Review

For production use, you may need to submit your app for Facebook review if you're requesting additional permissions beyond basic profile and email.

## Features Included

This implementation includes:

- ✅ Facebook OAuth login/signup
- ✅ Automatic account linking for existing email users
- ✅ Profile picture display
- ✅ User name display
- ✅ Graceful handling of Facebook-only vs. email+password users
- ✅ Proper session management
- ✅ CSRF protection

## Database Changes

The following fields have been added to the User model:
- `facebook_id`: Stores the user's Facebook ID
- `first_name`: User's first name from Facebook
- `last_name`: User's last name from Facebook  
- `profile_picture_url`: URL to user's Facebook profile picture
- `auth_provider`: Tracks how the user authenticated ('email', 'facebook', or 'both')

The `hashed_password` field is now nullable to support Facebook-only users. 