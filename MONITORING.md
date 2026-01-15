# Monitoring & Observability Guide

> **Version:** 1.0.0  
> **Last Updated:** January 2026

## Overview

This guide covers monitoring, logging, alerting, and debugging strategies for the Talenti AI Interview Platform.

---

## Table of Contents

1. [Logging Strategy](#logging-strategy)
2. [Log Analysis](#log-analysis)
3. [Metrics & KPIs](#metrics--kpis)
4. [Alerting](#alerting)
5. [Debugging Workflows](#debugging-workflows)
6. [Performance Monitoring](#performance-monitoring)

---

## Logging Strategy

### Edge Function Logging

All edge functions include structured logging:

```typescript
// Log levels and patterns
console.log(`[function-name] Info message`);
console.warn(`[function-name] Warning: ${details}`);
console.error(`[function-name] Error:`, error);

// Structured logging for key events
console.log(`[ai-interviewer] Request - User: ${userId}, Question: ${questionIndex}`);
console.log(`[ai-interviewer] Response - Tokens: ${usage}, Latency: ${ms}ms`);
```

### Log Categories

| Category | When to Log | Example |
|----------|-------------|---------|
| Auth | Login/logout, token generation | `User ${id} authenticated` |
| API | Incoming requests, responses | `POST /ai-interviewer - 200 (45ms)` |
| AI | Model calls, token usage | `Gemini call - 500 tokens, 1.2s` |
| Database | Queries, mutations | `Insert interview: ${id}` |
| Errors | All exceptions | `Error in scoring: ${message}` |
| Security | Auth failures, rate limits | `Rate limit: IP ${ip}` |

### Sensitive Data Handling

```typescript
// ❌ WRONG - Don't log PII
console.log(`User email: ${user.email}`);

// ✅ CORRECT - Log identifiers only
console.log(`User: ${user.id} authenticated`);

// ✅ CORRECT - Truncate sensitive data
console.log(`Token: ${token.slice(0, 8)}...`);
```

---

## Log Analysis

### Accessing Logs

#### Lovable Cloud Dashboard

1. Open project in Lovable
2. Navigate to "Backend" or use View Backend action
3. Select "Functions" → "Logs"
4. Filter by function name or time range

#### SQL Analytics Queries

```sql
-- Recent errors from all functions
SELECT 
  id, 
  timestamp, 
  event_message,
  metadata.level
FROM function_edge_logs
CROSS JOIN UNNEST(metadata) as metadata
WHERE metadata.level = 'error'
ORDER BY timestamp DESC
LIMIT 50;

-- Auth failures
SELECT 
  timestamp,
  event_message,
  metadata.path,
  metadata.status
FROM auth_logs
CROSS JOIN UNNEST(metadata) as metadata
WHERE metadata.status >= 400
ORDER BY timestamp DESC
LIMIT 100;

-- Database errors
SELECT 
  timestamp,
  event_message,
  parsed.error_severity
FROM postgres_logs
CROSS JOIN UNNEST(metadata) as m
CROSS JOIN UNNEST(m.parsed) as parsed
WHERE parsed.error_severity IN ('ERROR', 'FATAL')
ORDER BY timestamp DESC
LIMIT 50;
```

### Common Log Patterns

#### Successful Interview Flow
```
[ai-interviewer] Authenticated user: abc-123
[ai-interviewer] Request - Question: 0, Practice: false
[ai-interviewer] AI response received
[ai-interviewer] Response: 250 tokens
```

#### Rate Limit Hit
```
[acs-token-generator] Rate limit exceeded for IP: 203.0.113.1
```

#### AI Error
```
[score-interview] AI Gateway error: 429 Too Many Requests
[score-interview] Returning rate limit response
```

---

## Metrics & KPIs

### Business Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Interviews Completed | Successful interview sessions | Growth |
| Completion Rate | Started vs completed | >85% |
| Avg Interview Duration | Time per interview | 10-15 min |
| Candidate Satisfaction | Post-interview rating | >4.0/5.0 |
| Time to Hire | Application to offer | Decrease |

### Technical Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| API Latency (p50) | 50th percentile response | <200ms |
| API Latency (p99) | 99th percentile response | <2000ms |
| Error Rate | 5xx responses / total | <1% |
| AI Token Usage | Daily token consumption | Budget |
| Edge Function Duration | Execution time | <10s |

### Query for Metrics

```sql
-- Daily interview completion rate
SELECT 
  DATE(created_at) as date,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  ROUND(
    COUNT(*) FILTER (WHERE status = 'completed')::numeric / 
    COUNT(*)::numeric * 100, 2
  ) as completion_rate
FROM interviews
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Edge function performance
SELECT 
  function_id,
  AVG(execution_time_ms) as avg_latency,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY execution_time_ms) as p50,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_time_ms) as p99,
  COUNT(*) as requests
FROM function_edge_logs
CROSS JOIN UNNEST(metadata) as m
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY function_id
ORDER BY requests DESC;
```

---

## Alerting

### Critical Alerts (Immediate Response)

| Alert | Condition | Action |
|-------|-----------|--------|
| High Error Rate | 5xx > 5% for 5 min | Check logs, scale if needed |
| Auth Service Down | Auth failures > 90% | Check Supabase status |
| AI Gateway Down | 402/429 sustained | Check Lovable status |
| Database Connection | Postgres errors spike | Check connection limits |

### Warning Alerts (Review Within Hours)

| Alert | Condition | Action |
|-------|-----------|--------|
| Elevated Latency | p99 > 5s for 15 min | Investigate slow queries |
| Rate Limit Spikes | 429s > 100/min | Check for abuse |
| Token Budget | >80% daily budget | Review AI usage |
| Storage Growth | >80% capacity | Plan cleanup |

### Setting Up Alerts

Currently, Lovable Cloud doesn't have built-in alerting. Recommended approaches:

1. **Scheduled Health Checks**: Create a cron job to check key endpoints
2. **Log Monitoring**: Set up log forwarding to external service
3. **Database Triggers**: Create triggers for anomaly detection

```sql
-- Example: Alert on high interview failure rate
CREATE OR REPLACE FUNCTION check_interview_health()
RETURNS void AS $$
DECLARE
  failure_rate numeric;
BEGIN
  SELECT 
    COUNT(*) FILTER (WHERE status = 'cancelled')::numeric / 
    NULLIF(COUNT(*), 0)::numeric * 100
  INTO failure_rate
  FROM interviews
  WHERE created_at > NOW() - INTERVAL '1 hour';
  
  IF failure_rate > 20 THEN
    -- Log alert (could send to external webhook)
    RAISE WARNING 'High interview failure rate: %', failure_rate;
  END IF;
END;
$$ LANGUAGE plpgsql;
```

---

## Debugging Workflows

### Debugging Frontend Issues

1. **Open Browser DevTools** (F12)
2. **Check Console** for JavaScript errors
3. **Check Network** for failed requests
4. **Check React Query DevTools** for cache state

```typescript
// Enable React Query DevTools in development
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### Debugging Edge Function Issues

1. **Check Function Logs** in Lovable Cloud
2. **Look for Error Patterns**:
   - 401: Auth token issue
   - 403: RLS policy blocking
   - 429: Rate limiting
   - 500: Code error

3. **Test with curl**:
```bash
curl -X POST \
  https://hmktvnmqcenhxhshwdwc.supabase.co/functions/v1/ai-interviewer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[],"jobTitle":"Test","currentQuestionIndex":0}'
```

### Debugging Database Issues

1. **Check RLS Policies**:
```sql
-- Temporarily check what user would see
SET ROLE authenticated;
SET request.jwt.claims TO '{"sub": "user-uuid"}';
SELECT * FROM table_name;
RESET ROLE;
```

2. **Check Query Performance**:
```sql
EXPLAIN ANALYZE SELECT * FROM interviews WHERE application_id = 'uuid';
```

3. **Check Active Connections**:
```sql
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

### Common Issues & Solutions

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| 401 on all requests | Token expired | Re-authenticate user |
| Empty query results | RLS blocking | Check policy logic |
| Slow queries | Missing index | Add appropriate index |
| AI timeout | Long transcript | Reduce input size |
| Recording missing | Retention cleanup | Check retention settings |

---

## Performance Monitoring

### Frontend Performance

```typescript
// Measure component render time
import { useEffect } from 'react';

function useRenderTime(componentName: string) {
  useEffect(() => {
    const start = performance.now();
    return () => {
      const duration = performance.now() - start;
      if (duration > 100) {
        console.warn(`${componentName} slow render: ${duration}ms`);
      }
    };
  });
}
```

### API Performance

```typescript
// Add timing to edge functions
const start = Date.now();

// ... do work ...

const duration = Date.now() - start;
console.log(`[function] Completed in ${duration}ms`);

// Return timing header
return new Response(body, {
  headers: {
    'X-Response-Time': `${duration}ms`,
    ...corsHeaders,
  },
});
```

### Database Performance

```sql
-- Slow query log
ALTER DATABASE postgres SET log_min_duration_statement = 1000;

-- Query statistics
SELECT 
  query,
  calls,
  mean_time,
  max_time,
  rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

### Performance Checklist

- [ ] Indexes on frequently queried columns
- [ ] Pagination on large result sets
- [ ] React Query stale times configured
- [ ] Images lazy loaded
- [ ] Components memoized where appropriate
- [ ] Large lists virtualized

---

## Health Check Endpoint

Consider implementing a health check function:

```typescript
// supabase/functions/health-check/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

serve(async (req) => {
  const checks = {
    database: false,
    ai_gateway: false,
    storage: false,
  };

  try {
    // Check database
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_ANON_KEY')!
    );
    const { error: dbError } = await supabase.from('organisations').select('id').limit(1);
    checks.database = !dbError;

    // Check AI gateway
    const aiResponse = await fetch('https://ai.gateway.lovable.dev/v1/models', {
      headers: { Authorization: `Bearer ${Deno.env.get('LOVABLE_API_KEY')}` }
    });
    checks.ai_gateway = aiResponse.ok;

    // Check storage
    const { error: storageError } = await supabase.storage.getBucket('candidate-cvs');
    checks.storage = !storageError;

    const healthy = Object.values(checks).every(c => c);
    
    return new Response(JSON.stringify({ healthy, checks }), {
      status: healthy ? 200 : 503,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    return new Response(JSON.stringify({ healthy: false, error: error.message }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
});
```

---

## Appendix: Useful Queries

### Daily Activity Summary

```sql
SELECT 
  DATE(created_at) as date,
  (SELECT COUNT(*) FROM applications WHERE DATE(created_at) = DATE(i.created_at)) as applications,
  COUNT(*) as interviews,
  COUNT(*) FILTER (WHERE status = 'completed') as completed,
  AVG(duration_seconds) as avg_duration
FROM interviews i
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### User Activity

```sql
SELECT 
  cp.user_id,
  cp.email,
  COUNT(DISTINCT a.id) as applications,
  COUNT(DISTINCT i.id) as interviews,
  MAX(i.created_at) as last_interview
FROM candidate_profiles cp
LEFT JOIN applications a ON a.candidate_id = cp.user_id
LEFT JOIN interviews i ON i.application_id = a.id
GROUP BY cp.user_id, cp.email
ORDER BY last_interview DESC NULLS LAST
LIMIT 50;
```

### Error Rate by Function

```sql
SELECT 
  m.function_id,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE response.status_code >= 500) as errors,
  ROUND(
    COUNT(*) FILTER (WHERE response.status_code >= 500)::numeric / 
    COUNT(*)::numeric * 100, 2
  ) as error_rate
FROM function_edge_logs
CROSS JOIN UNNEST(metadata) as m
CROSS JOIN UNNEST(m.response) as response
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY m.function_id
ORDER BY error_rate DESC;
```
