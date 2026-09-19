# New Railway services cannot use `railway.toml`

**Date:** 2026-09-19 · **Area:** Deployment

## What happened

The plan for #2 was to commit a `railway.toml` pointing Railway at the Dockerfile, with a healthcheck and watch paths. Railway's docs now say config as code is deprecated, and that new services cannot opt into it at all.

> "New services cannot opt into Config as Code. Existing Config as Code files stop being read on 2026-12-01 (hard cutoff)."

Its replacement is a `.railway/railway.ts` file applied with `railway config plan` / `railway config apply` from the Railway CLI. Railway does not read `.railway/` during deploys.

## Why

A product change at Railway. Many examples online still show `railway.toml`.

## What we do about it

For #2:

- The Dockerfile sits at the repo root, where Railway finds it without any configuration.
- The healthcheck path, watch paths and replica count are set once in the Railway dashboard. [Deployment](../setup/deployment.md) lists them.
- No `railway.toml` in the repo.

## Sources

- https://docs.railway.com/infrastructure-as-code
- https://docs.railway.com/reference/config-as-code
- https://docs.railway.com/builds/dockerfiles
