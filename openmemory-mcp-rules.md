# Dead Frontier Auto Trading System - OpenMemory MCP Usage Rules

## OpenMemory MCP Integration Rules

### When to Use OpenMemory MCP

#### **Required Usage Scenarios**

1. **User Preferences and Settings Storage**
   ```
   Trigger: When user provides specific configuration preferences or trading parameters
   Tools: mcp_openmemory_add-memory
   Purpose: Persist user preferences across sessions and conversations
   ```

2. **Error Pattern Recognition and Solutions**
   ```
   Trigger: When encountering and solving new error scenarios
   Tools: mcp_openmemory_add-memory + mcp_openmemory_search-memories
   Purpose: Build a knowledge base of error patterns and proven solutions
   ```

3. **Page Structure Changes Documentation**
   ```
   Trigger: When detecting changes in Dead Frontier web interface
   Tools: mcp_openmemory_add-memory
   Purpose: Track website evolution and maintain selector compatibility
   ```

4. **Session Context Preservation**
   ```
   Trigger: At the start of each conversation or when context is needed
   Tools: mcp_openmemory_search-memories
   Purpose: Retrieve relevant project context and previous learnings
   ```

#### **Recommended Usage Scenarios**

5. **Successful Strategy Documentation**
   ```
   Trigger: When discovering effective trading strategies or anti-detection methods
   Tools: mcp_openmemory_add-memory
   Purpose: Build a repository of proven techniques and configurations
   ```

6. **Code Pattern and Best Practice Storage**
   ```
   Trigger: When implementing effective code solutions or architecture decisions
   Tools: mcp_openmemory_add-memory
   Purpose: Maintain consistency and reuse successful patterns
   ```

7. **User Feedback and Corrections**
   ```
   Trigger: When user corrects assumptions or provides important clarifications
   Tools: mcp_openmemory_add-memory
   Purpose: Learn from user feedback to improve future interactions
   ```

#### **Do Not Use Scenarios**

8. **Sensitive Information**
   ```
   Reason: Never store passwords, API keys, or personal sensitive data
   Alternative: Use environment variables or secure configuration files
   ```

9. **Temporary Debug Information**
   ```
   Reason: Avoid cluttering memory with short-term debugging data
   Alternative: Use logging systems or temporary files
   ```

---

## Memory Management Workflow

### Phase 1: Context Retrieval
```
1. At conversation start, search for relevant project memories
2. Query user preferences and previous configurations
3. Retrieve error patterns and known solutions
4. Load successful strategies and proven approaches
```

### Phase 2: Active Learning
```
1. Monitor for new user preferences or corrections
2. Document successful problem resolutions
3. Record effective trading strategies
4. Note changes in website structure or behavior
```

### Phase 3: Knowledge Consolidation
```
1. Periodically review and organize stored memories
2. Update outdated information when website changes
3. Consolidate similar patterns and strategies
4. Remove obsolete or incorrect information
```

---

## Memory Categories and Usage Patterns

### 1. **User Preferences**
```markdown
Category: User Configuration
Format: "User prefers [specific setting/approach] for [context/scenario]"
Examples:
- "User prefers conservative trading approach with 20% profit margins"
- "User wants notifications disabled during night hours (10PM-6AM)"
- "User prefers Chrome browser over Firefox for better stability"
```

### 2. **Error Solutions**
```markdown
Category: Error Resolution
Format: "Error: [description] | Solution: [steps taken] | Context: [when it occurs]"
Examples:
- "Error: Login timeout after 30s | Solution: Increase timeout to 60s and add retry logic | Context: Peak server load times"
- "Error: Element not found for buy button | Solution: Updated selector to use data-testid attribute | Context: After website update on 2024-01-15"
```

### 3. **Website Changes**
```markdown
Category: Site Evolution
Format: "Change detected: [what changed] | Date: [when] | Impact: [affected functionality]"
Examples:
- "Change detected: Marketplace search moved from #searchBox to .search-input | Date: 2024-01-20 | Impact: Search automation updated"
- "Change detected: New CAPTCHA system on login page | Date: 2024-02-01 | Impact: Enhanced anti-detection required"
```

### 4. **Successful Strategies**
```markdown
Category: Trading Strategy
Format: "Strategy: [approach] | Success Rate: [percentage] | Context: [when to use]"
Examples:
- "Strategy: Buy items under 50% market value, sell at 80% | Success Rate: 85% | Context: Non-peak hours with stable market"
- "Strategy: Use random delays between 2-5 seconds for actions | Success Rate: 95% | Context: Avoiding detection algorithms"
```

---

## Best Practices

### 1. **Memory Search Optimization**
- Use specific keywords when searching memories
- Search at conversation start for relevant context
- Query memories before implementing solutions to check for previous experience
- Use broad terms first, then narrow down with specific queries

### 2. **Memory Storage Best Practices**
- Store information immediately when user provides preferences
- Use clear, descriptive titles for easy retrieval
- Include context and date information when relevant
- Avoid duplicating similar information

### 3. **Memory Maintenance**
- Regularly update outdated website structure information
- Remove obsolete error patterns when site changes
- Consolidate similar strategies to avoid confusion
- Verify stored information accuracy periodically

### 4. **Privacy and Security**
- Never store login credentials or sensitive user data
- Avoid storing personal information beyond preferences
- Use generic descriptions for error patterns
- Focus on technical patterns rather than personal details

---

## Specific Application Examples

### Example 1: User Preference Storage
```markdown
Scenario: User mentions they prefer conservative trading

Steps:
1. mcp_openmemory_add-memory -> Store: "User prefers conservative trading approach with lower risk tolerance"
2. Future sessions automatically retrieve this preference
3. Trading parameters adjusted accordingly without re-asking
```

### Example 2: Error Pattern Learning
```markdown
Scenario: Solving a new login detection issue

Steps:
1. mcp_openmemory_search-memories -> Query similar login issues
2. Apply known solutions or develop new approach
3. mcp_openmemory_add-memory -> Store successful solution
4. Future occurrences reference this solution first
```

### Example 3: Website Change Adaptation
```markdown
Scenario: Marketplace layout changes detected

Steps:
1. Document the change with mcp_openmemory_add-memory
2. Update relevant selectors and code
3. Store new selector patterns for future reference
4. Search memories when similar changes occur
```

---

## Integration with Development Workflow

### With Playwright MCP
```
- Use OpenMemory to store successful element locators discovered via Playwright
- Remember anti-detection strategies that proved effective
- Document page interaction patterns that work consistently
```

### With Python Development
```
- Store configuration patterns that work well for specific scenarios
- Remember code solutions for recurring problems
- Document successful error handling approaches
```

### With Testing and Debugging
```
- Store test scenarios that consistently reproduce issues
- Remember debugging approaches that led to solutions
- Document environmental factors that affect performance
```

---

## Development Efficiency Benefits

Using OpenMemory MCP provides:

1. **Persistent Context** - No need to re-explain preferences or previous decisions
2. **Accumulated Wisdom** - Build a knowledge base of what works and what doesn't
3. **Faster Problem Resolution** - Quickly reference previous solutions to similar issues
4. **Consistent Behavior** - Maintain user preferences across all interactions
5. **Adaptive Learning** - System becomes more effective over time

---

## Memory Lifecycle Management

### Daily Operations
- Search memories at conversation start
- Add new learnings as they occur
- Update strategies based on results

### Weekly Review
- Consolidate similar memories
- Update outdated information
- Remove obsolete entries

### Major Updates
- Document significant website changes
- Update strategy effectiveness ratings
- Reorganize memory categories if needed

Remember: **OpenMemory enables continuous learning and improvement across all project interactions!** 