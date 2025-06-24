# Dead Frontier Auto Trading System

A Python-based automated trading bot for Dead Frontier marketplace using Playwright for web automation.

## Features

- **Automated Trading**: Buy low, sell high with intelligent market analysis
- **Anti-Detection**: Advanced human behavior simulation to avoid detection
- **Risk Management**: Built-in risk assessment and portfolio management
- **Data Persistence**: SQLAlchemy-based data storage with migration support
- **Configurable**: Flexible configuration system with environment variables
- **Modular Design**: Clean, extensible architecture

## Project Structure

```
Dfautotrans/
├── src/dfautotrans/           # Main package
│   ├── core/                  # Core business logic
│   ├── automation/            # Browser automation and anti-detection
│   ├── data/                  # Data models and database operations
│   ├── config/                # Configuration management
│   ├── utils/                 # Utility functions and helpers
│   ├── strategies/            # Trading strategies
│   └── api/                   # API interfaces (optional)
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
└── js/                        # Original JavaScript implementation
```

## Installation

### Prerequisites

- Python 3.11+
- uv package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Dfautotrans
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Install Playwright browsers:
```bash
uv run playwright install
```

4. Copy environment configuration:
```bash
cp env.example .env
```

5. Edit `.env` with your settings

## Usage

### Basic Usage

```bash
# Run with default settings
uv run python main.py

# Run in headless mode
uv run python main.py --headless

# Run in debug mode
uv run python main.py --debug

# Test mode (no actual trades)
uv run python main.py --dry-run
```

### Configuration

Edit the `.env` file to customize:

- Trading parameters (target items, price limits, etc.)
- Browser settings (headless mode, timeouts)
- Risk management settings
- Anti-detection parameters

## Development

### Using Playwright MCP

This project supports Playwright MCP for development and testing. See `PROJECT_RULES.md` for usage guidelines.

### Development Environment

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run black src/ tests/

# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## Project Rules

- Use Playwright MCP for page analysis and interaction testing
- Follow the development workflow outlined in `PROJECT_RULES_EN.md`
- Test thoroughly before production deployment
- Use MCP for development, Python code for production

## License

This project is for educational purposes only. Please respect the terms of service of Dead Frontier.

## Contributing

1. Follow the project rules in `PROJECT_RULES_EN.md`
2. Use Playwright MCP for testing new features
3. Write tests for new functionality
4. Follow the established code style 