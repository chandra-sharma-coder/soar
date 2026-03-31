# URLscan.io FastAPI SOAR Connector

A modern, FastAPI-based connector for URLscan.io that provides a clean SDK-style interface for SOAR platforms.

## Features

- ✅ **Clean Architecture**: Separation of concerns with clients, services, and actions
- ✅ **Type Safety**: Full type hints and Pydantic validation
- ✅ **Auto Documentation**: Interactive API docs with Swagger UI and ReDoc
- ✅ **Error Handling**: Comprehensive error handling and validation
- ✅ **Async Support**: Built on FastAPI for high performance
- ✅ **Extensible**: Easy to add new endpoints and functionality

## Project Structure

```
urlscan_fastapi/
├── app/
│   ├── __init__.py                 # Package initialization
│   ├── main.py                     # FastAPI application entry point
│   ├── routes.py                   # API route definitions
│   ├── run.py                      # Development server launcher
│   ├── requirements.txt            # Python dependencies
│   ├── actions/                    # Action handlers (business logic)
│   │   ├── __init__.py
│   │   ├── detonate_url.py
│   │   ├── get_report.py
│   │   └── lookup_domain.py
│   ├── clients/                    # External API clients
│   │   ├── __init__.py
│   │   └── urlscan_client.py
│   ├── core/                       # Core configuration
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/                     # Data models and schemas
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/                   # Service layer
│       ├── __init__.py
│       └── urlscan_service.py
├── test_api.py                     # API test script
└── .env.example                    # Environment variables template
```

## Installation

### 1. Install Dependencies

```bash
cd urlscan_fastapi
pip install -r app/requirements.txt
```

### 2. Configure Environment (Optional)

Create a `.env` file from the example:

```bash
copy .env.example .env
```

Edit `.env` and add your URLscan.io API key (optional for public scans):

```env
URLSCAN_API_KEY=your_api_key_here
```

> Note: An API key is optional but recommended for higher rate limits and private scans.

## Running the Application

### Development Server

```bash
cd urlscan_fastapi
python app/run.py
```

The server will start on `http://localhost:8000`

### Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### 1. Detonate URL (Submit for Scanning)

**Endpoint**: `POST /api/v1/detonate_url`

**Request Body**:
```json
{
  "url": "https://example.com"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "URL submitted successfully for scanning",
  "data": [
    {
      "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "url": "https://example.com"
    }
  ],
  "summary": {
    "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "submitted_url": "https://example.com"
  }
}
```

### 2. Get Report

**Endpoint**: `POST /api/v1/get_report`

**Request Body**:
```json
{
  "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Report fetched successfully",
  "data": [
    {
      "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "url": "https://example.com",
      "ip": "93.184.216.34",
      "country": "US"
    }
  ],
  "summary": {
    "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "url": "https://example.com",
    "ip": "93.184.216.34",
    "country": "US"
  }
}
```

### 3. Lookup Domain

**Endpoint**: `POST /api/v1/lookup_domain`

**Request Body**:
```json
{
  "domain": "example.com"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Domain lookup successful: found 10 results",
  "data": [
    {
      "task": {...},
      "stats": {...},
      "page": {...}
    }
  ],
  "summary": {
    "domain": "example.com",
    "result_count": 10
  }
}
```

## Testing

Run the test script to verify all endpoints:

```bash
cd urlscan_fastapi
python test_api.py
```

The test script will:
1. Check server health
2. Submit a URL for scanning
3. Search for a domain
4. Retrieve the scan report (after waiting for scan completion)

## Architecture

### Layers

1. **Routes Layer** (`routes.py`)
   - Defines HTTP endpoints
   - Handles request/response serialization
   - Maps HTTP requests to actions

2. **Actions Layer** (`actions/`)
   - Implements business logic
   - Orchestrates service calls
   - Formats responses for API consumers

3. **Services Layer** (`services/`)
   - Business logic and data transformation
   - Intermediary between actions and clients
   - Aggregates and processes API responses

4. **Clients Layer** (`clients/`)
   - Direct communication with external APIs
   - HTTP request handling
   - Low-level error handling

5. **Models Layer** (`models/`)
   - Pydantic schemas for validation
   - Request/response type definitions
   - Data validation rules

6. **Core Layer** (`core/`)
   - Configuration management
   - Shared utilities
   - Environment variables

### Benefits of This Architecture

- **Separation of Concerns**: Each layer has a specific responsibility
- **Testability**: Easy to mock and test individual components
- **Maintainability**: Changes in one layer don't affect others
- **Scalability**: Easy to add new endpoints or external services
- **Type Safety**: Full type checking with Pydantic and type hints

## Development

### Adding a New Endpoint

1. Create action in `actions/` directory
2. Add method to service in `services/`
3. Add client method in `clients/` (if needed)
4. Define request/response schemas in `models/schemas.py`
5. Add route in `routes.py`

### Code Style

- Use type hints for all function parameters and return values
- Add docstrings to all classes and public methods
- Follow PEP 8 style guidelines
- Use meaningful variable and function names

## Troubleshooting

### Server won't start

- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check Python version (requires Python 3.7+)

### API returns errors

- Verify URLscan.io API is accessible
- Check your API key (if using one)
- Review server logs for detailed error messages

### Import errors

- Make sure all `__init__.py` files are present
- Run from the correct directory (`urlscan_fastapi/`)
- Verify Python path includes the app directory

## License

This project is part of the URLscan.io SOAR connector implementation.

## Contributing

When contributing:
1. Maintain the existing architecture
2. Add tests for new functionality
3. Update documentation
4. Follow the code style guidelines
