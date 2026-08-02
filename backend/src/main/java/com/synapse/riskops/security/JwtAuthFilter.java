package com.synapse.riskops.security;

/**
 * JwtAuthFilter.java
 * Owner: Person 2 | Week: 8 (per README's phased plan) — full auth lockdown
 *
 * Validates JWT tokens on incoming requests, sets Spring Security authentication
 * context. SecurityConfig.java currently permits all requests (Phase 1 — see its
 * comments); this filter gets wired in once auth is implemented, replacing the
 * permissive .anyRequest().permitAll() rule.
 */
public class JwtAuthFilter {
    // TODO Week 8: implement JWT validation filter
}
