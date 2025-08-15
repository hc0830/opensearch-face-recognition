# Contributing to OpenSearch Face Recognition System

Thank you for your interest in contributing to the OpenSearch Face Recognition System! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues
- Use the appropriate issue template
- Provide detailed information about the problem
- Include steps to reproduce the issue
- Add relevant logs and error messages

### Suggesting Features
- Use the feature request template
- Explain the use case and business value
- Consider alternative solutions
- Provide implementation ideas if possible

### Contributing Code
1. Fork the repository
2. Create a feature branch from `develop`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation
7. Submit a pull request

## 🏗️ Development Setup

### Prerequisites
- Node.js >= 14.x
- Python >= 3.8
- AWS CLI configured
- CDK CLI installed

### Local Development
```bash
# Clone your fork
git clone https://github.com/your-username/opensearch-face-recognition.git
cd opensearch-face-recognition

# Install dependencies
make install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run tests
make test

# Build project
make build
```

## 📝 Coding Standards

### Python Code
- Follow PEP 8 style guide
- Use Black for code formatting
- Add type hints where appropriate
- Write docstrings for functions and classes
- Maximum line length: 127 characters

### JavaScript/TypeScript Code
- Follow ESLint configuration
- Use Prettier for formatting
- Add JSDoc comments for functions
- Use meaningful variable names

### Git Commit Messages
Follow the conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
- `feat(api): add face deletion endpoint`
- `fix(search): resolve similarity threshold bug`
- `docs(readme): update installation instructions`

## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=lambda_functions tests/
```

### Writing Tests
- Write unit tests for all new functions
- Include integration tests for API endpoints
- Mock external services (AWS, OpenSearch)
- Test both success and error scenarios
- Aim for >80% code coverage

### Test Structure
```
tests/
├── unit/
│   ├── test_lambda_functions.py
│   └── test_utils.py
├── integration/
│   ├── test_api.py
│   └── test_opensearch.py
└── fixtures/
    ├── sample_images.py
    └── mock_responses.py
```

## 📚 Documentation

### Code Documentation
- Add docstrings to all public functions
- Include parameter types and return values
- Provide usage examples
- Document any side effects

### API Documentation
- Update OpenAPI/Swagger specs
- Include request/response examples
- Document error codes and messages
- Add authentication requirements

### README Updates
- Keep installation instructions current
- Update feature lists
- Add new configuration options
- Include troubleshooting tips

## 🔄 Pull Request Process

### Before Submitting
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with develop

### PR Requirements
- Use the pull request template
- Link to related issues
- Describe changes clearly
- Include test results
- Add screenshots if UI changes

### Review Process
1. Automated checks must pass
2. At least one maintainer review required
3. Address all review comments
4. Squash commits before merge

## 🏷️ Labeling System

### Issue Labels
- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to docs
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on

### Priority Labels
- `priority/critical`: Critical issue
- `priority/high`: High priority
- `priority/medium`: Medium priority
- `priority/low`: Low priority

### Status Labels
- `status/needs-triage`: Needs initial review
- `status/in-progress`: Currently being worked on
- `status/blocked`: Blocked by external dependency
- `status/ready-for-review`: Ready for code review

## 🚀 Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Git tag created
- [ ] Release notes written

## 🛡️ Security

### Reporting Security Issues
- Do not open public issues for security vulnerabilities
- Use GitHub Security Advisories
- Email maintainers directly for critical issues
- Provide detailed reproduction steps

### Security Best Practices
- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all inputs
- Follow AWS security best practices
- Keep dependencies updated

## 📞 Getting Help

### Community Support
- GitHub Discussions for questions
- Issue tracker for bugs and features
- Wiki for documentation

### Maintainer Contact
- Create an issue for project-related questions
- Use discussions for general questions
- Email for security issues only

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to the OpenSearch Face Recognition System!
