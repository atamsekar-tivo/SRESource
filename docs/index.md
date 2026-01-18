# SRESource - Production Debugging & Operations Guide

Welcome to **SRESource**, your comprehensive reference guide for production debugging, operations, and troubleshooting.

## 📖 What is SRESource?

SRESource is a **self-hosted knowledge base** designed for Site Reliability Engineers (SREs), DevOps professionals, and Platform Engineers. It provides:

- **60+ Production Scenarios** with step-by-step debugging procedures
- **400+ Production-Ready Commands** across multiple platforms
- **~30,000 Lines** of curated, battle-tested content
- **FAANG-Level Best Practices** from high-performing engineering teams
- **Multi-Platform Coverage** - Kubernetes, Linux, Cloud, Databases, CI/CD

## 🎯 Quick Navigation

### Core Topics

| Topic | Purpose |
|-------|---------|
| [**Kubernetes Debugging**](kubernetes-debugging-commands.md) | Pod scheduling, network, storage, RBAC issues |
| [**EKS Production Guide**](production-debugging-eks.md) | AWS EKS cluster creation, upgrades, debugging |
| [**Unix/Linux Debugging**](production-debugging-unix-linux.md) | System performance, resources, troubleshooting |
| [**Network Debugging**](production-networking-debugging.md) | Connectivity, DNS, firewalls, multi-cloud networking |
| [**CI/CD Tools**](production-debugging-ci-cd-tools.md) | Jenkins, GitHub Actions, ArgoCD, GitLab CI debugging |
| [**IAM & Access Control**](production-debugging-iam.md) | Kubernetes RBAC, AWS IAM, GCP/Azure permissions |
| [**Database Debugging**](production-debugging-databases.md) | MySQL & PostgreSQL production issues |
| [**Essential Tools**](TOOLS_GUIDE.md) | 150+ curated tools for SRE/DevOps teams |

## 🚀 Getting Started

### For First-Time Users

1. **Start with your problem domain** - Use the navigation menu above
2. **Find the relevant scenario** - Each guide has 12-15 production scenarios
3. **Follow the diagnostic steps** - 12-step procedures for each issue
4. **Use the provided commands** - Production-ready commands ready to run
5. **Refer to notes** - Dangerous commands marked with ❌ NEVER

### Example: Quick Query

```
Problem: Kubernetes pod stuck in CrashLoopBackOff
Solution: See Kubernetes Debugging → "Pod CrashLoopBackOff" section
Steps: Follow 12-step diagnostic procedure
Commands: Copy/paste ready-to-run kubectl commands
```

## 📊 Content Breakdown

### By Platform

- **Kubernetes**: 2 guides (cluster, EKS)
- **Operating Systems**: Linux/Unix debugging
- **Cloud**: IAM, EKS, multi-cloud
- **Networking**: Pod-to-pod, cross-cluster, hybrid
- **Databases**: MySQL, PostgreSQL
- **CI/CD**: 5 platforms covered
- **Tools**: 150+ tools categorized

### By Complexity

- **Beginner**: Connection issues, basic diagnostics
- **Intermediate**: Performance tuning, optimization
- **Advanced**: Lock contention, replication, HA failover

### By Severity

- **Critical**: Service down, data loss risk
- **High**: Performance degradation, security issues
- **Medium**: Resource warnings, slow operations
- **Low**: Best practices, optimization opportunities

## ✨ Key Features

### 🔍 Full-Text Search
Use the search box to find topics across all guides instantly.

### 🌙 Dark Mode
Toggle between light and dark themes for comfortable reading.

### 💻 Code Highlighting
All commands and code blocks include syntax highlighting.

### 📱 Mobile-Friendly
Access guides on desktop, tablet, or mobile seamlessly.

### 📎 Last Updated
Each page shows when it was last modified.

### 📖 Auto-Generated Index
Navigate with automatic table of contents on each page.

## 🎓 Learning Path

### Week 1: Foundation
- [ ] Read: Essential Tools Guide
- [ ] Read: Kubernetes Debugging - Basics
- [ ] Read: Linux Debugging - Fundamentals
- [ ] Lab: Deploy sample application

### Week 2-3: Intermediate
- [ ] Read: Network Debugging
- [ ] Read: Database Debugging - MySQL/PostgreSQL basics
- [ ] Lab: Simulate common issues
- [ ] Lab: Perform diagnosis and recovery

### Week 4+: Advanced
- [ ] Read: EKS Production Guide
- [ ] Read: IAM & Access Control
- [ ] Read: CI/CD Platform debugging
- [ ] Lab: Multi-environment deployment
- [ ] Lab: Build your own runbooks

## ⚠️ Important Notes

### Use With Care

- All commands are **production-ready** but should be tested in **staging first**
- Commands marked with ❌ **NEVER** can cause **permanent data loss** if misused
- Always have a **verified backup** before making changes
- Read-only commands are safe for production exploration

### Best Practices

1. **Understand before executing** - Read the full scenario before running commands
2. **Start with diagnostics** - Run read-only commands first
3. **Document changes** - Keep records of modifications
4. **Test in staging** - All changes should be tested first
5. **Have rollback plans** - Be prepared to undo changes

## 🔗 External Resources

- [Kubernetes Official Docs](https://kubernetes.io/docs/)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Linux Man Pages](https://man7.org/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 📝 Contributing

Found an error? Have a useful command to share? Contributions are welcome!

Visit the [GitHub Repository](https://github.com/atamsekar-tivo/SRESource) to contribute.

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/atamsekar-tivo/SRESource/issues)
- **Discussions**: [GitHub Discussions](https://github.com/atamsekar-tivo/SRESource/discussions)

## 📄 License

SRESource is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) - feel free to share and adapt!

---

## 🎯 Quick Command Reference

```bash
# Search across all guides (Ctrl+K or Cmd+K)
# Use dark mode toggle (top right)
# Navigate with sidebar
# Use back button to go to previous page
```

## 💡 Pro Tips

- **Bookmark your favorites** - Use browser bookmarks for frequently-used guides
- **Print to PDF** - Save guides offline for reference
- **Share with team** - Link directly to specific sections
- **Add to wiki** - Reference from your internal documentation

---

**Start exploring now!** Select a guide from the navigation menu above or use search to find specific topics.

**Last Updated**: January 2026  
**Total Content**: ~30,000 lines | 60+ scenarios | 400+ commands  
**License**: CC BY-SA 4.0