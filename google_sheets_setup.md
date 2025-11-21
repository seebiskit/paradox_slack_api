# Google Sheets Integration Setup

## 1. Set Environment Variables

Add these to your `.env` file:

```bash
# Google Sheets Configuration
GOOGLE_SHEETS_ACCESS_TOKEN=your_oauth_token_here
GOOGLE_SHEET_ID=your_sheet_id_here
WORKSHEET_NAME=Metrics
```

## 2. Get Your Credentials

### Google Sheets Access Token
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Sheets API
3. Create OAuth 2.0 credentials
4. Generate access token with scope: `https://www.googleapis.com/auth/spreadsheets`

### Google Sheet ID
From your Google Sheets URL:
`https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit`

The Sheet ID is: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

## 3. Test the Connection

Run the test script:
```bash
python google_sheets_sync.py
```

You should see: `✅ Google Sheets connection successful!`

## 4. Sheet Structure

The integration will automatically create these headers:

| Date       | Category              | Metric   | Value | Units  | User         | Notes     |
|------------|----------------------|----------|-------|--------|--------------|-----------|
| 2025-11-21 | 11 AM Sermon Attendance | Adults   | 100   | people | Sawyer Martin| Great day |
| 2025-11-21 | 11 AM Sermon Attendance | Children | 50    | people | Sawyer Martin| Great day |

## 5. Looker Studio Connection

1. In Looker Studio, click "Add Data"
2. Select "Google Sheets" 
3. Choose your metrics spreadsheet
4. Select the "Metrics" worksheet
5. Start building dashboards!

## 6. Features

- ✅ **Real-time sync** - Data appears immediately after metric submission
- ✅ **Auto-headers** - Correct column headers created automatically  
- ✅ **Error handling** - Graceful fallback if Google Sheets is unavailable
- ✅ **User tracking** - Shows who logged each metric
- ✅ **Notes included** - All context preserved for analysis

## Troubleshooting

- **401 Unauthorized**: Check your access token
- **404 Not Found**: Verify your Sheet ID
- **Connection failed**: Ensure Google Sheets API is enabled
- **No data syncing**: Check environment variables are set correctly