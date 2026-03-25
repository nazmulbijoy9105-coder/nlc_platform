# NLC Platform Agents & Customizations

This document provides an overview of available agents and customized workflows for the **nlc_platform** project. Agents are specialized AI assistants that are automatically selected based on your task context.

## Available Agents

### 🚀 DevOps & Deployment Specialist
**File**: `.github/agents/devops-deployment.agent.md`

**Specialization**: Infrastructure, deployments, containerization, database operations

**Use this agent when:**
- Deploying to Render, Fly.io, or Vercel
- Managing Docker and Docker Compose
- Running database migrations with Alembic
- Configuring environment variables and secrets
- Managing Celery workers and tasks
- Checking system health and monitoring
- Performing backups and disaster recovery
- Troubleshooting infrastructure issues

**Example prompts:**
```
@DevOps & Deployment Specialist: Prepare the production deployment checklist
@DevOps & Deployment Specialist: Help me restore the database from S3 backup
@DevOps & Deployment Specialist: Debug the Celery worker task queue
@DevOps & Deployment Specialist: Configure health monitoring for the staging environment
@DevOps & Deployment Specialist: Run the database migration and verify it succeeded
```

**Key Focus Areas:**
- Deployment workflows and procedures
- Container orchestration
- Database migrations and seeding
- Celery worker task management
- Health checks and monitoring
- Backup and disaster recovery

---

### 📋 Rule Engine & Compliance Specialist
**File**: `.github/agents/rule-engine.agent.md`

**Specialization**: Business rules, compliance logic, ILRMF standards

**Use this agent when:**
- Implementing new compliance rules
- Debugging rule evaluation failures
- Designing ILRMF compliance workflows
- Creating rule services and operations
- Writing rule-related tests
- Managing rule state transitions
- Designing compliance check logic
- Working with the rules engine

**Example prompts:**
```
@Rule Engine & Compliance Specialist: Add a new filing requirement compliance rule
@Rule Engine & Compliance Specialist: Debug why the compliance check is failing
@Rule Engine & Compliance Specialist: Design a rule for company registration validation
@Rule Engine & Compliance Specialist: Implement state transition logic for compliance status
@Rule Engine & Compliance Specialist: Write unit tests for the rule engine evaluation
```

**Key Focus Areas:**
- Rule engine architecture and evaluation
- Compliance logic implementation
- ILRMF standard compliance
- Rule service operations
- Compliance state management
- Business rule validation

---

### 💻 FastAPI Backend Developer
**File**: `.github/agents/fastapi-backend.agent.md`

**Specialization**: API development, services, models, database operations

**Use this agent when:**
- Building new API endpoints
- Implementing service methods
- Designing database models and schemas
- Handling request/response validation
- Working on authentication and authorization
- Implementing business logic
- Performing data schema and database design
- Writing API integration tests

**Example prompts:**
```
@FastAPI Backend Developer: Create an API endpoint to list all companies with filtering
@FastAPI Backend Developer: Implement the filing service with proper error handling
@FastAPI Backend Developer: Design the database model for new document types
@FastAPI Backend Developer: Add authentication to the admin endpoints
@FastAPI Backend Developer: Write integration tests for the filing API
```

**Key Focus Areas:**
- FastAPI route development
- Service layer implementation
- SQLAlchemy model design
- Pydantic schema validation
- Authentication and security
- API documentation

---

## Agent Selection Guide

### Task: Deploy to Production
→ **Use**: DevOps & Deployment Specialist
```
@DevOps & Deployment Specialist: Prepare and execute production deployment
```

### Task: Add New Compliance Rule
→ **Use**: Rule Engine & Compliance Specialist
```
@Rule Engine & Compliance Specialist: Implement a new compliance rule for filing requirements
```

### Task: Create Company Management API
→ **Use**: FastAPI Backend Developer
```
@FastAPI Backend Developer: Create CRUD endpoints for company management
```

### Task: Debug Service Integration Issue
→ **Use**: Depends on component:
- **If compliance-related**: Rule Engine Specialist
- **If API route-related**: FastAPI Backend Developer
- **If infrastructure-related**: DevOps Specialist

### Task: Implement Scheduled Background Job
→ **Use**: DevOps & Deployment Specialist (for scheduling) + FastAPI Backend if implementing the job itself

---

## Workflow Examples

### Example 1: Implement New Compliance Feature

**Step 1**: Design the compliance rule
```
@Rule Engine & Compliance Specialist: Design a compliance rule for company registration
```

**Step 2**: Create the database model and service
```
@FastAPI Backend Developer: Create the database model and service for this compliance rule
```

**Step 3**: Add API endpoint
```
@FastAPI Backend Developer: Add an endpoint to check compliance status
```

**Step 4**: Deploy to production
```
@DevOps & Deployment Specialist: Deploy the latest changes to production
```

### Example 2: Debug Production Issue

**Step 1**: Investigate the issue
```
@DevOps & Deployment Specialist: Check the application logs and health status
```

**Step 2**: If rule-related
```
@Rule Engine & Compliance Specialist: Debug the failing compliance check
```

**Step 3**: If API-related
```
@FastAPI Backend Developer: Debug the endpoint implementation
```

**Step 4**: Deploy fix
```
@DevOps & Deployment Specialist: Apply the fix and verify deployment
```

### Example 3: Add New Feature

**Step 1**: Plan the feature
- Rule Engine: What compliance rules apply?
- Backend: What API endpoints needed?
- DevOps: What infrastructure changes?

**Step 2**: Implement in order
1. Database models (FastAPI Backend)
2. Business logic/rules (Rule Engine)
3. API endpoints (FastAPI Backend)
4. Tests (Both agents can help)
5. Deploy (DevOps)

---

## Best Practices

### ✅ DO:
- **Be Specific**: Tell the agent exactly what you're trying to do
- **Provide Context**: Share relevant files, error messages, or requirements
- **One Focus Per Request**: Keep each request to a single logical task
- **Name the Agent**: Use `@AgentName:` to explicitly select an agent
- **Include Error Details**: Share stack traces, logs, or error messages

### ❌ DON'T:
- Mix multiple tasks in one request (break into separate requests)
- Ask DevOps for code review (that's for default agent or teammates)
- Ask Backend for deployment details (that's DevOps)
- Ask Rule Engine for API endpoint details (that's Backend)
- Assume agent context from previous message (be explicit each time)

---

## Project Architecture at a Glance

```
nlc_platform/
├── .github/
│   └── agents/                        # Specialized agent configurations
│       ├── devops-deployment.agent.md
│       ├── rule-engine.agent.md
│       └── fastapi-backend.agent.md
├── app/
│   ├── api/                           # FastAPI routes → Backend Agent
│   ├── models/                        # Database models → Backend Agent
│   ├── services/                      # Business logic → Rule Engine or Backend
│   ├── rule_engine/                   # Rules evaluation → Rule Engine Agent
│   ├── worker/                        # Celery tasks → DevOps Agent
│   └── core/                          # Config, security → Backend Agent
├── alembic/                           # Database migrations → DevOps Agent
├── scripts/                           # Deployment/automation → DevOps Agent
├── tests/                             # Unit & integration tests → Relevant agents
├── docker-compose.yml                 # Container config → DevOps Agent
└── render.yaml, fly.toml, vercel.json # Platform configs → DevOps Agent
```

---

## Integration with Version Control

These agents work seamlessly with your development workflow:

1. **Create Branch**: Ask agents to implement features
2. **Commit Changes**: Agents provide clear commit messages
3. **Create PR**: Agents explain changes and impact
4. **Code Review**: Ask relevant agent for implementation details
5. **Test**: Agents help write and run tests
6. **Deploy**: Use DevOps agent for deployment
7. **Monitor**: Use DevOps agent for post-deployment monitoring

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Agent doing general coding instead of specialized | Be explicit: `@DevOps & Deployment Specialist:` |
| Confusion about responsibility | Check the agent selection guide above |
| Agent suggests wrong approach | Provide more context or ask different agent |
| Need multiple perspectives | Ask each relevant agent separately |

---

## Getting Started

1. **For Deployments**: Try
   ```
   @DevOps & Deployment Specialist: What's the current deployment status?
   ```

2. **For Compliance Work**: Try
   ```
   @Rule Engine & Compliance Specialist: Show me how compliance rules are implemented
   ```

3. **For API Development**: Try
   ```
   @FastAPI Backend Developer: Show me the pattern for creating a new API endpoint
   ```

---

## Support & Feedback

To refine or update these agents:
1. Edit the `.agent.md` files directly
2. Adjust tool permissions based on needs
3. Update descriptions for clarity
4. Document new procedures as needed

All agents share the same codebase and context—they're just configured differently for specific task domains.
