# Dead Frontier Auto Trading System - Project Development Rules

## Playwright MCP Usage Rules

### When to Use Playwright MCP

#### **Required Usage Scenarios**

1. **Page Structure Analysis Phase**
   ```
   Trigger: When needing to understand new pages or page structure changes
   Tools: mcp_playwright_browser_navigate + mcp_playwright_browser_snapshot
   Purpose: Get complete DOM structure and interactive elements
   ```

2. **Element Locator Development**
   ```
   Trigger: When writing new element selectors or existing selectors fail
   Tools: mcp_playwright_browser_snapshot + element analysis
   Purpose: Find the most stable and reliable element location methods
   ```

3. **Interaction Flow Verification**
   ```
   Trigger: Before implementing new interaction logic
   Tools: Complete MCP tool chain
   Purpose: Verify the feasibility and stability of interaction steps
   ```

4. **Error Scenario Debugging**
   ```
   Trigger: When Python code encounters interaction issues
   Tools: mcp_playwright_browser_snapshot + specific operation testing
   Purpose: Understand error causes and find solutions
   ```

#### **Recommended Usage Scenarios**

5. **Anti-Detection Strategy Testing**
   ```
   Trigger: When developing or optimizing anti-detection mechanisms
   Tools: mcp_playwright_browser_* series tools
   Purpose: Quickly test the effectiveness of different strategies
   ```

6. **New Feature Prototype Development**
   ```
   Trigger: For feasibility verification before implementing new features
   Tools: Choose appropriate tools based on specific needs
   Purpose: Quickly validate ideas and get feedback
   ```

#### **Do Not Use Scenarios**

7. **Production Environment**
   ```
   Reason: MCP is mainly for development and testing, not suitable for production
   Alternative: Use final Python + Playwright code
   ```

8. **High-Frequency Repetitive Operations**
   ```
   Reason: MCP calls have delays, not suitable for high-efficiency batch operations
   Alternative: Write dedicated Python scripts
   ```

---

## Development Workflow

### Phase 1: Page Analysis
```
1. Use MCP to navigate to target pages
2. Get page snapshots and structure
3. Analyze key elements and interaction points
4. Record selectors and interaction patterns
```

### Phase 2: Prototype Development
```
1. Use MCP to test basic interactions
2. Verify buy/sell processes
3. Test error handling
4. Optimize element location strategies
```

### Phase 3: Python Implementation
```
1. Write Python code based on MCP test results
2. Implement BrowserManager and related modules
3. Integrate anti-detection and human behavior simulation
4. Conduct integration testing
```

### Phase 4: Verification and Optimization
```
1. Use MCP to verify correctness of Python implementation
2. Compare MCP test results with Python execution results
3. Optimize performance and stability
4. Final verification
```

---

## Best Practices

### 1. **Page Analysis Best Practices**
- Always get page snapshot before performing operations
- Record multiple selector options for important elements
- Pay attention to page loading states and dynamic content

### 2. **Element Interaction Best Practices**
- Verify element existence before interaction
- Test different clicking and input methods
- Consider possible element state changes

### 3. **Error Handling Best Practices**
- Test various error scenarios
- Record error responses and recovery strategies
- Verify timeout and retry mechanisms

### 4. **Performance Considerations**
- MCP calls have delays, don't overuse
- Arrange call order reasonably when batch analyzing
- Save important analysis results to avoid repeated calls

---

## Specific Application Examples

### Example 1: Analyze Market Page Structure
```markdown
Goal: Understand the marketplace page product list structure

Steps:
1. mcp_playwright_browser_navigate -> marketplace URL
2. mcp_playwright_browser_snapshot -> Get complete page structure
3. Analyze .fakeItem elements and their attributes
4. Record selectors for price, quantity, seller information
5. Test search functionality interaction methods
```

### Example 2: Verify Purchase Flow
```markdown
Goal: Test complete product purchase process

Steps:
1. Navigate to marketplace and get snapshot
2. mcp_playwright_browser_click -> Click target product
3. mcp_playwright_browser_snapshot -> Check product details page
4. mcp_playwright_browser_click -> Click buy button
5. mcp_playwright_browser_snapshot -> Check confirmation dialog
6. Test confirm and cancel operations
```

### Example 3: Inventory Management Analysis
```markdown
Goal: Analyze inventory page product management functionality

Steps:
1. Switch to selling tab
2. Get inventory area snapshot
3. Analyze inventory item element structure
4. Test right-click menu and selling functionality
5. Verify price input and confirmation process
```

---

## Development Efficiency Improvement

Using Playwright MCP can:

1. **Accelerate Development** - Quickly understand and test web interactions
2. **Reduce Errors** - Discover and solve potential issues in advance
3. **Improve Quality** - Better element location and error handling
4. **Facilitate Maintenance** - Quickly adapt when website structure changes

Remember: **MCP is a development tool, Python code is the final product**! 