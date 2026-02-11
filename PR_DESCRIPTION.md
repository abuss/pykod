# Pull Request: Add Debian/Ubuntu multi-distribution support

**Branch:** `multi_dist`  
**Target:** `main`  
**PR URL:** https://github.com/abuss/pykod/compare/main...multi_dist

---

## Summary

This PR adds comprehensive Debian and Ubuntu distribution support to pykod while maintaining full backward compatibility with Arch Linux.

### Key Features
- ✅ Support for Debian (stable, bookworm, testing, etc.)
- ✅ Support for Ubuntu (24.04 noble, 22.04 jammy, etc.)
- ✅ Single `Debian` class handles both variants via parameter
- ✅ **Repository components support** (main, universe, multiverse, non-free, etc.)
- ✅ Full backward compatibility - no breaking changes to Arch
- ✅ Distribution-specific GPU driver packages
- ✅ Comprehensive documentation and examples

### Architecture Changes

Created a two-tier repository class hierarchy:
- **`Repository`** (ABC) - Base class with package management methods
  - Used by auxiliary repos: AUR, Flatpak
  - Methods: `install_packages()`, `remove_packages()`, `update_installed_packages()`, `is_valid_packages()`
- **`BaseSystemRepository`** (extends Repository) - For distributions with base system installation
  - Used by: Arch, Debian
  - Additional methods: `install_base()`, `get_base_packages()`, `get_kernel_info()`, `setup_linux()`, `generate_initramfs()`, `update_database()`

### Implementation Details

**Debian Repository Class:**
- Uses `debootstrap` for base installation (vs Arch's `pacstrap`)
- Uses `apt-get` for package management (vs Arch's `pacman`)
- Uses `dracut` for initramfs generation (consistent with Arch)
- Kernel location: `/boot/vmlinuz-<version>` (vs Arch's `/usr/lib/modules/`)
- Default release: `"stable"` (automatically tracks Debian stable branch)
- **Repository components**: Configurable via `components` parameter
  - Ubuntu defaults: `["main", "universe"]` (matches Ubuntu Desktop)
  - Debian defaults: `["main"]` (minimal installation)
  - Users can add: `multiverse`, `restricted`, `contrib`, `non-free`, etc.

**Distribution-Specific Package Mappings:**
```python
# Arch
nvidia = ["nvidia", "nvidia-utils", "nvidia-settings"]

# Debian/Ubuntu  
nvidia = ["nvidia-driver", "nvidia-settings"]
```

### Files Changed

**New Files:**
- `src/pykod/repositories/debian.py` - Full Debian/Ubuntu implementation (267 lines)
- `example/configuration-debian.py` - Debian stable example
- `example/configuration-ubuntu.py` - Ubuntu 24.04 example
- `DEBIAN_IMPLEMENTATION_PLAN.md` - Detailed implementation tracking

**Modified Files:**
- `src/pykod/repositories/base.py` - Added abstract base classes
- `src/pykod/repositories/arch.py` - Added `generate_initramfs()`, inherit from `BaseSystemRepository`
- `src/pykod/core.py` - Use repository method for initramfs
- `src/pykod/config.py` - Use repository method in hooks
- `src/pykod/repositories/__init__.py` - Export new classes
- `README.md` - Comprehensive multi-distro documentation (311 new lines)

### Testing

✅ All configurations load successfully:
```bash
python example/configuration-debian.py --help  # ✓ Works
python example/configuration-ubuntu.py --help  # ✓ Works
python example/configuration.py --help          # ✓ Arch still works
```

✅ Syntax validation: All Python files compile without errors  
✅ Import tests: `from pykod.repositories import Debian` works  
✅ Backward compatibility: Existing Arch configurations unchanged

### Usage Examples

**Debian Stable:**
```python
from pykod.repositories import Debian

debian = Debian()  # Uses "stable" release
conf = Configuration(base=debian)
```

**Debian Bookworm:**
```python
debian = Debian(release="bookworm")
```

**Ubuntu 24.04:**
```python
ubuntu = Debian(release="noble", variant="ubuntu")
conf = Configuration(base=ubuntu)
# Defaults to components=["main", "universe"]
```

**Ubuntu with all repositories:**
```python
ubuntu = Debian(
    release="noble", 
    variant="ubuntu",
    components=["main", "universe", "multiverse", "restricted"]
)
```

**Debian with non-free:**
```python
debian = Debian(components=["main", "contrib", "non-free"])
```

### Design Decisions

1. **Single `Debian` class** with `variant` parameter (vs separate `Ubuntu` class)
   - Simplifies code reuse - Ubuntu and Debian are very similar
   - Variant parameter clearly indicates the distribution type
   
2. **Default to `"stable"`** release for Debian
   - Automatically tracks Debian's stable branch
   - Users can override with specific codenames if needed

3. **Always use `dracut`** for initramfs on Debian
   - Consistent with Arch implementation
   - Reliable and well-tested

4. **Runtime package validation** (no pre-validation)
   - Let apt fail with clear error messages
   - Avoids complexity of maintaining package databases

5. **Repository components with smart defaults**
   - Ubuntu: `["main", "universe"]` by default (matches Ubuntu Desktop behavior)
   - Debian: `["main"]` by default (minimal, users add contrib/non-free as needed)
   - User can override via `components` parameter
   - Uses debootstrap's native `--components` flag

### Backward Compatibility

- ✅ No changes to existing Arch API
- ✅ No changes to existing configuration files
- ✅ All changes are additive only
- ✅ AUR and Flatpak continue to work as before

### Documentation

- ✅ Updated README with quick start guides for each distribution
- ✅ Added package name comparison tables
- ✅ Documented GPU driver package mappings per distro
- ✅ Added release/version configuration examples
- ✅ Documented repository components feature (main, universe, multiverse, etc.)

### Next Steps

This PR enables:
- Users can now use pykod on Debian and Ubuntu systems
- Same declarative configuration approach across all distros
- Future expansion to other distributions (Fedora, etc.)

---

**Stats:** 
- Initial implementation: +1311 lines, -18 lines
- Components feature: +134 lines, -6 lines
- **Total:** +1445 lines, -24 lines across 10 files

**Commits:**
- `6a213c8` - Add Debian/Ubuntu multi-distribution support
- `773bb62` - Add repository components support for Debian/Ubuntu
