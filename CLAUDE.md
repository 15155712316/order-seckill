# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Setup

### Virtual Environment
```powershell
# Activate virtual environment (Windows)
venv\Scripts\Activate.ps1

# OR on Linux/Mac
source venv/bin/activate
```

### Dependencies
The project uses Python 3.12.4 with the following key packages:
- PyQt6 (GUI framework)
- aiohttp (HTTP client for async API calls)
- gTTS (Text-to-speech)
- playsound (Audio playback)
- pandas (Data processing)
- requests (HTTP requests)
- pycryptodome (Encryption/decryption)
- Flask (Web server for API)

### Running the Application
```bash
# Main GUI application
python main.py

# Web API server (optional)
python web_server.py
```

## Architecture Overview

### Core Components

**Main Application Flow:**
- `main.py` - Entry point with single instance checking and GUI initialization
- `ui/main_window.py` - Primary PyQt6 GUI with tabbed interface for monitoring and strategy management
- `core/engine.py` - Central rule engine that processes orders against user-defined strategies

**Data Layer:**
- `core/database.py` - SQLite database manager for strategies, settings, and user authentication
- `config.py` - Centralized configuration for API endpoints, network settings, and application constants

**Platform Integration:**
- `core/platforms/base_adapter.py` - Abstract base class defining platform adapter interface
- `core/platforms/haha_adapter.py` - Integration with "哈哈" platform API
- `core/platforms/mahua_adapter.py` - Integration with "麻花" platform API

**Security & Authentication:**
- `core/auth.py` - "Guardian Shield" authentication system with hardware fingerprinting
- Machine code generation for device binding
- Online user authentication against remote server

**Audio & Notifications:**
- `core/audio.py` - TTS (Text-to-Speech) system for order alerts
- Cached audio files in `tts_cache/` directory
- Configurable alert templates for different scenarios

### Strategy Engine Architecture

The application supports two main strategy types:

1. **Keyword Strategies** - Match orders based on:
   - City filtering
   - Cinema name keywords (AND logic)
   - Hall type inclusion/exclusion
   - Profit calculations with hall costs
   - Weekday filtering

2. **Whitelist Strategies** - Match orders based on:
   - Predefined cinema whitelists stored in database
   - Movie title filtering with OR logic
   - Advanced filtering (ticket counts, price ranges, minimum bid)
   - Specialized profit calculations

### Async Architecture

The application uses Qt's signal/slot system combined with asyncio:
- `Worker` class runs in separate thread for API polling
- Platform adapters handle concurrent API requests
- Real-time order processing with deduplication
- Status updates via PyQt signals

### Data Flow

1. **Order Monitoring:** Worker thread polls platform APIs every 5 seconds
2. **Data Processing:** Each platform adapter standardizes order format
3. **Rule Matching:** RuleEngine evaluates orders against active strategies
4. **Alert Generation:** Matching orders trigger TTS alerts and GUI updates
5. **Storage:** Orders and strategy data persist in SQLite database

## Database Schema

The application uses SQLite with tables for:
- `strategies` - User-defined trading strategies
- `whitelist_cinemas` - Cinema names for whitelist strategies  
- `settings` - Application configuration and platform credentials
- `users` - Authentication data (when applicable)

## Configuration Management

### Platform Credentials
Sensitive API tokens and keys are stored in database `settings` table, not in code:
- Haha platform: `token` field
- Mahua platform: `dev_code` and `secret_key` fields

### Network Configuration
Located in `config.py`:
- Request timeouts and retry logic
- SSL verification settings
- API endpoints for both platforms

## Security Considerations

The application implements "Guardian Shield" security:
- Hardware fingerprinting prevents unauthorized usage
- Single instance enforcement
- Platform credentials encrypted in database
- No hardcoded secrets in source code

## Testing & Development

### Logging
Application uses Python logging with dual output:
- Console output for real-time debugging
- `app.log` file for persistent logging
- Configurable log levels in `config.py`

### Database Debugging
Direct database inspection:
- `orders.db` contains all application data
- Use SQLite browser or CLI tools for inspection

### Platform Testing
Each platform adapter includes:
- Connection testing methods
- Error handling for authentication failures
- Request/response logging for debugging

## Common Development Tasks

### Adding New Platform
1. Create new adapter inheriting from `BaseAdapter`
2. Implement `fetch_and_process()` method
3. Add platform configuration to `config.py`
4. Update UI to include new platform credentials
5. Register adapter in `Worker.init_platform_adapters()`

### Modifying Strategy Logic
- Core logic in `RuleEngine.check_order()` and `WhitelistPolicy.check()`
- Strategy persistence handled automatically via database
- UI updates driven by `policies_updated` signal

### Audio Customization
- TTS templates in `config.py`
- Audio caching system prevents redundant generation
- Whitelist strategies use specialized alert text

## File Structure Context

```
抢单提醒/
├── main.py                 # Application entry point
├── config.py              # Configuration constants
├── web_server.py          # Optional HTTP API server
├── orders.db              # SQLite database
├── app.log                # Application logs
├── tts_cache/             # Cached audio files
├── core/                  # Core application logic
│   ├── engine.py          # Strategy matching engine
│   ├── database.py        # Database operations
│   ├── auth.py            # Authentication system
│   ├── audio.py           # Text-to-speech
│   └── platforms/         # Platform integrations
│       ├── base_adapter.py
│       ├── haha_adapter.py
│       └── mahua_adapter.py
├── ui/                    # User interface
│   └── main_window.py     # Main PyQt6 window
└── venv/                  # Python virtual environment
```

This is a sophisticated order monitoring and alert system for automated ticket purchasing platforms with multi-strategy support and real-time notifications.