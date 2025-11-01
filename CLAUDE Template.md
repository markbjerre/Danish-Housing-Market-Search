# Project: My Awesome App

## Project Description
A brief description of what your project does and its main features.

## Tech Stack
- Frontend: 
- Backend: 
- Database: 
- Testing: 

## Code Conventions
- We use Prettier for formatting
- Functional components with hooks
- 2-space indentation
- camelCase for variables and functions
- PascalCase for components and classes

## Project Structure
- /src - Main source code
  - /components -  components
  - /pages - Page components
  - /api - API routes
  - /utils - Utility functions
  - /hooks - Custom hooks
  - /styles - Styles
- /public - Static assets
- /tests - Test files

Step 2: Add Context-Specific Sections
Enhance your CLAUDE.md with more specific context:

## Important Notes
- User authentication uses JWT stored in HttpOnly cookies
- API calls should use the client utility in /src/utils/api.ts
- New components should have a companion test file

## Known Issues


## Future Plans

Take your CLAUDE.md file to the next level with these advanced features:

Custom Instructions
Add specific instructions for how Claude should behave when working with your project:

## Instructions for Claude
- Always suggest TypeScript types for new functions
- Prioritize performance optimizations
- Use SQL Query for data fetching
- Follow the existing error handling pattern
- Include JSDoc comments for public functions
- Prefer functional programming approaches
Environment Configuration
Provide information about the development environment:

## Environment Setup

- Environment variables (examples, not actual values):
Architecture Diagrams

Mermaid diagrams to visualize architecture:

## Architecture

```mermaid
# EXAMPLE
graph TD
    A[Client] --> B[API Gateway]
    B --> C[Auth Service]
    B --> D[User Service]
    B --> E[Content Service]
    C --> F[(Auth DB)]
    D --> G[(User DB)]
    E --> H[(Content DB)]
```

## Component Relationships

```mermaid
# EXAMPLE
graph TD
    A[App] --> B[Layout]
    B --> C[Header]
    B --> D[Main Content]
    B --> E[Footer]
    D --> F[Dashboard]
    F --> G[UserStats]
    F --> H[ActivityFeed]
    F --> I[Recommendations]
```