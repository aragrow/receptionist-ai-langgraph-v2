# Phase 12.3: User Feedback Loop - Implementation Complete

## 📦 Files Created/Modified

### 1. **src/models/database_models.py** (Modified)
- ✅ Added `uuid` import
- ✅ Added `FeedbackType` enum
- ✅ Added `FeedbackCategory` enum  
- ✅ Added `PromptVersion` model
- ✅ Added `PromptPerformance` model
- ✅ Added `MisclassifiedIntent` model
- ✅ Added `UserFeedback` model
- ✅ Added `EscalationFeedback` model
- ✅ Added `FeedbackAnalytics` model
- ✅ Updated `__all__` export list

### 2. **src/services/feedback_service.py** (Created)
- ✅ `FeedbackService` class with full functionality
- ✅ `collect_feedback()` - collect user ratings
- ✅ `collect_escalation_feedback()` - collect escalation feedback
- ✅ `get_feedback_summary()` - get feedback metrics
- ✅ `generate_analytics()` - comprehensive analytics
- ✅ `get_improvement_opportunities()` - list improvement opportunities
- ✅ `update_improvement_opportunity()` - update opportunities
- ✅ Automatic pattern detection for negative feedback
- ✅ Automatic creation of improvement opportunities

### 3. **main.py** (Modified)
- ✅ Added `feedback_service` initialization
- ✅ Added 6 new feedback endpoints
- ✅ Updated health check with feedback status
- ✅ Updated root endpoint with new features
- ✅ Updated stats endpoint with feedback metrics

---

## 🚀 Getting Started

### Installation

No new dependencies needed! All functionality uses existing libraries.

### Database Collections

The following collections will be auto-created on first use:
- `user_feedback` - stores user feedback
- `escalation_feedback` - stores escalation feedback
- `feedback_analytics` - stores generated analytics
- `improvement_opportunities` - stores identified improvements
- `prompt_versions` - stores prompt versions (Phase 12.1/12.2)
- `prompt_performance` - stores prompt metrics (Phase 12.1/12.2)
- `misclassified_intents` - stores misclassifications (Phase 12.1/12.2)

---

## 📡 API Endpoints

### Feedback Collection

#### 1. Submit User Feedback
```http
POST /feedback
Content-Type: application/json

{
  "session_id": "session_12345",
  "feedback_type": "thumbs_up",
  "agent_name": "receptionist_l1",
  "rating": 5,
  "feedback_text": "Very helpful!",
  "category": "helpfulness",
  "intent": "scheduling"
}
```

**Response:**
```json
{
  "success": true,
  "feedback_id": "fb_uuid",
  "message": "Thank you for your feedback! We use it to improve our service."
}
```

**Feedback Types:**
- `thumbs_up`
- `thumbs_down`
- `rating` (use with rating field 1-5)
- `text_feedback`

**Categories:**
- `accuracy`
- `speed`
- `helpfulness`
- `understanding`
- `resolution`
- `other`

#### 2. Submit Escalation Feedback
```http
POST /feedback/escalation
Content-Type: application/json

{
  "ticket_id": "ticket_001",
  "session_id": "session_12345",
  "escalation_reason": "Complex billing issue",
  "was_escalation_necessary": false,
  "user_satisfaction": 4,
  "resolved": true,
  "resolution_time_minutes": 15,
  "could_have_been_automated": true,
  "suggested_improvement": "Add billing FAQ to knowledge base"
}
```

**Response:**
```json
{
  "success": true,
  "feedback_id": "fb_uuid",
  "message": "Thank you for your feedback! This helps us improve our escalation handling."
}
```

### Analytics & Reporting

#### 3. Get Feedback Summary
```http
GET /feedback/summary?agent_name=receptionist_l1&days=7
```

**Response:**
```json
{
  "period_days": 7,
  "total_feedback": 150,
  "positive_feedback": 120,
  "negative_feedback": 20,
  "neutral_feedback": 10,
  "positive_rate": 0.8,
  "avg_rating": 4.2,
  "category_breakdown": {
    "helpfulness": 50,
    "accuracy": 40,
    "speed": 30
  },
  "intent_breakdown": {
    "scheduling": {
      "total": 60,
      "positive": 50,
      "negative": 5
    },
    "billing": {
      "total": 40,
      "positive": 30,
      "negative": 8
    }
  },
  "agent_name": "receptionist_l1"
}
```

#### 4. Get Comprehensive Analytics
```http
GET /feedback/analytics?period_days=30
```

**Response:**
```json
{
  "analytics_id": "analytics_uuid",
  "period_start": "2025-09-01T00:00:00Z",
  "period_end": "2025-10-01T00:00:00Z",
  "total_feedback_count": 500,
  "positive_feedback_count": 400,
  "negative_feedback_count": 80,
  "avg_rating": 4.3,
  "feedback_by_agent": {
    "receptionist_l1": {
      "total": 200,
      "positive": 170,
      "negative": 20
    },
    "sales_agent_l3": {
      "total": 150,
      "positive": 130,
      "negative": 15
    }
  },
  "feedback_by_intent": {
    "scheduling": {
      "total": 180,
      "positive": 160,
      "negative": 15
    }
  },
  "top_issues": [
    {
      "category": "understanding",
      "count": 25,
      "percentage": 0.31
    },
    {
      "category": "accuracy",
      "count": 20,
      "percentage": 0.25
    }
  ],
  "improvement_opportunities": [
    "High negative feedback rate: 10 occurrences",
    "Could have been automated"
  ]
}
```

### Improvement Tracking

#### 5. Get Improvement Opportunities
```http
GET /improvements?status=open&priority=high&limit=10
```

**Response:**
```json
{
  "opportunities": [
    {
      "opportunity_id": "opp_uuid_1",
      "created_at": "2025-10-01T12:00:00Z",
      "agent_name": "receptionist_l1",
      "intent": "billing",
      "issue_description": "High negative feedback rate: 10 occurrences",
      "sample_feedback": [
        "Didn't understand my billing question",
        "Needed to escalate for simple query"
      ],
      "status": "open",
      "priority": "high",
      "assigned_to": null,
      "resolved": false
    }
  ],
  "count": 1
}
```

**Query Parameters:**
- `status`: `open`, `in_progress`, `resolved`
- `priority`: `high`, `medium`, `low`
- `limit`: max results (default: 20)

#### 6. Update Improvement Opportunity
```http
PUT /improvements/opp_uuid_1
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_to": "john@example.com",
  "resolution_notes": "Added billing FAQ to knowledge base"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Improvement opportunity opp_uuid_1 updated successfully"
}
```

---

## 🧪 Testing the Feedback System

### Test 1: Submit Positive Feedback

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_001",
    "feedback_type": "thumbs_up",
    "agent_name": "receptionist_l1",
    "rating": 5,
    "feedback_text": "Great service!",
    "category": "helpfulness",
    "intent": "scheduling"
  }'
```

### Test 2: Submit Negative Feedback (Triggers Analysis)

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_002",
    "feedback_type": "thumbs_down",
    "agent_name": "receptionist_l1",
    "rating": 2,
    "feedback_text": "Did not understand my request",
    "category": "understanding",
    "intent": "billing"
  }'
```

### Test 3: Create Pattern (5+ negative feedback)

Run this 5 times with different session IDs to trigger pattern detection:

```bash
for i in {1..5}; do
  curl -X POST http://localhost:8000/feedback \
    -H "Content-Type: application/json" \
    -d "{
      \"session_id\": \"test_session_pattern_$i\",
      \"feedback_type\": \"thumbs_down\",
      \"agent_name\": \"billing_agent_l3\",
      \"rating\": 1,
      \"feedback_text\": \"Billing issue not resolved\",
      \"category\": \"resolution\",
      \"intent\": \"billing\"
    }"
done
```

This should automatically create an improvement opportunity!

### Test 4: Submit Escalation Feedback

```bash
curl -X POST http://localhost:8000/feedback/escalation \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "ticket_001",
    "session_id": "test_session_003",
    "escalation_reason": "Complex technical issue",
    "was_escalation_necessary": false,
    "user_satisfaction": 3,
    "resolved": true,
    "resolution_time_minutes": 45,
    "could_have_been_automated": true,
    "suggested_improvement": "Add technical troubleshooting guide"
  }'
```

### Test 5: Get Feedback Summary

```bash
curl http://localhost:8000/feedback/summary?days=7
```

### Test 6: Get Analytics

```bash
curl http://localhost:8000/feedback/analytics?period_days=30
```

### Test 7: Check Improvement Opportunities

```bash
curl http://localhost:8000/improvements?status=open&priority=high
```

### Test 8: Update an Opportunity

```bash
# First get an opportunity_id from the previous call, then:
curl -X PUT http://localhost:8000/improvements/YOUR_OPPORTUNITY_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "assigned_to": "developer@example.com",
    "resolution_notes": "Working on improving billing agent responses"
  }'
```

---

## 🎯 Integration with Existing Workflow

### After Each Call Response

In your frontend or client application, prompt users for feedback:

```javascript
// After receiving response from /process-call
const callResponse = await fetch('/process-call', {
  method: 'POST',
  body: JSON.stringify(callRequest)
});

const result = await callResponse.json();

// Show feedback prompt to user
showFeedbackPrompt({
  sessionId: result.session_id,
  agentName: result.current_agent || 'unknown',
  intent: result.intent
});

// When user provides feedback
async function submitFeedback(rating) {
  await fetch('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: result.session_id,
      feedback_type: rating >= 4 ? 'thumbs_up' : 'thumbs_down',
      agent_name: result.current_agent,
      rating: rating,
      intent: result.intent
    })
  });
}
```

### After Escalation Resolution

```javascript
// When closing an escalation ticket
async function closeTicketWithFeedback(ticketId, sessionId) {
  const feedback = await promptUserForEscalationFeedback();
  
  await fetch('/feedback/escalation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticket_id: ticketId,
      session_id: sessionId,
      escalation_reason: feedback.reason,
      was_escalation_necessary: feedback.necessary,
      user_satisfaction: feedback.satisfaction,
      resolved: true,
      resolution_time_minutes: feedback.timeToResolve
    })
  });
}
```

---

## 📊 Monitoring & Alerts

### Automatic Pattern Detection

The system automatically:
- ✅ Detects patterns of negative feedback (5+ within 7 days)
- ✅ Creates improvement opportunities
- ✅ Flags unnecessary escalations
- ✅ Identifies automation opportunities

### Check Logs

```bash
tail -f logs/ai_receptionist.log | grep -E "Pattern detected|improvement opportunity"
```

You'll see entries like:
```
⚠️ Pattern detected: Multiple negative feedback for billing_agent_l3/billing (10 occurrences in last 7 days)
💡 Created improvement opportunity: opp_12345
```

---

## 🔄 Weekly Review Process

### 1. Review Analytics Dashboard

```bash
curl http://localhost:8000/feedback/analytics?period_days=7 | jq
```

### 2. Check Open Improvements

```bash
curl http://localhost:8000/improvements?status=open | jq
```

### 3. Prioritize High-Impact Issues

Focus on improvements with:
- High frequency (10+ occurrences)
- Low satisfaction scores (<3)
- High automation potential

### 4. Assign and Track

```bash
# Assign to team member
curl -X PUT http://localhost:8000/improvements/OPP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "assigned_to": "team-member@company.com"
  }'
```

### 5. Mark as Resolved

After implementing fixes:

```bash
curl -X PUT http://localhost:8000/improvements/OPP_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolved": true,
    "resolution_notes": "Updated prompt and added FAQ entries"
  }'
```

---

## 🎨 Frontend Integration Example

### Simple Feedback Widget

```html
<!-- Add after each AI response -->
<div class="feedback-widget">
  <p>Was this response helpful?</p>
  <button onclick="submitFeedback('thumbs_up', 5)">👍 Yes</button>
  <button onclick="submitFeedback('thumbs_down', 2)">👎 No</button>
</div>

<script>
async function submitFeedback(type, rating) {
  await fetch('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: currentSessionId,
      feedback_type: type,
      agent_name: currentAgent,
      rating: rating,
      intent: currentIntent
    })
  });
  
  showThankYouMessage();
}
</script>
```

---

## 📈 Success Metrics

Track these KPIs over time:

1. **Positive Feedback Rate**: Target > 80%
2. **Average Rating**: Target > 4.0/5
3. **Unnecessary Escalation Rate**: Target < 10%
4. **Time to Resolve Improvements**: Target < 2 weeks
5. **Feedback Response Rate**: Target > 30%

---

## 🚨 Common Issues & Solutions

### Issue: No feedback being recorded

**Check:**
```bash
# Verify feedback_service is initialized
curl http://localhost:8000/health | jq '.feedback_enabled'

# Check database connection
mongo ai_receptionist --eval "db.user_feedback.count()"
```

### Issue: Improvement opportunities not being created

**Requirement:** Need 5+ similar negative feedback within 7 days

**Test manually:**
```python
# Run this in Python to create test feedback
import asyncio
from datetime import datetime, timezone
from src.services.feedback_service import FeedbackService
from src.services.database_service import DatabaseService

async def test():
    db = DatabaseService()
    await db.connect()
    fs = FeedbackService(db)
    
    # Create 5 negative feedback
    for i in range(5):
        await fs.collect_feedback(
            session_id=f"test_{i}",
            feedback_type="thumbs_down",
            agent_name="test_agent",
            rating=1,
            intent="test_intent"
        )
    
    # Check opportunities
    opps = await fs.get_improvement_opportunities()
    print(f"Created {len(opps)} opportunities")

asyncio.run(test())
```

---

## ✅ Phase 12.3 Complete!

You now have a fully functional feedback collection and analysis system that:

✅ Collects user feedback on interactions  
✅ Tracks escalation effectiveness  
✅ Automatically detects patterns  
✅ Creates improvement opportunities  
✅ Provides comprehensive analytics  
✅ Enables continuous improvement  

**Next Steps:**
- Integrate feedback widgets into your frontend
- Set up weekly review process
- Monitor improvement opportunities
- Use analytics to guide prompt optimization (Phase 12.1/12.2)

---

## 📚 Related Documentation

- **Phase 12.1**: Prompt Tuning System (coming next)
- **Phase 12.2**: Model Optimization (coming next)
- **API Documentation**: http://localhost:8000/docs
- **System Health**: http://localhost:8000/health
