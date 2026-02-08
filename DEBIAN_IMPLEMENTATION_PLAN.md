# Debian Support Implementation Plan

**Status:** ✅ COMPLETED  
**Started:** 2025-02-07  
**Completed:** 2025-02-07  
**Objective:** Add Debian/Ubuntu distribution support to pykod

---

## Implementation Progress

### Phase 1: Enhance Repository Base Class ✅ COMPLETED
- [x] Add abstract methods to `src/pykod/repositories/base.py`
- [x] Verify syntax

### Phase 2: Update Arch Implementation ✅ COMPLETED
- [x] Add `generate_initramfs()` to `src/pykod/repositories/arch.py`
- [x] Verify syntax

### Phase 3: Update Core Boot Logic ✅ COMPLETED
- [x] Update `src/pykod/core.py` line 215
- [x] Update `src/pykod/config.py` line 774
- [x] Verify syntax

### Phase 4: Create Debian Repository Class ✅ COMPLETED
- [x] Create `src/pykod/repositories/debian.py`
- [x] Implement all required methods
- [x] Add GPU_PACKAGES dictionary
- [x] Verify syntax

### Phase 5: Update Repository Exports ✅ COMPLETED
- [x] Update `src/pykod/repositories/__init__.py`
- [x] Verify import works

### Phase 6: Create Example Configurations ✅ COMPLETED
- [x] Create `example/configuration-debian.py`
- [x] Create `example/configuration-ubuntu.py`
- [x] Verify configurations load

### Phase 7: Documentation Updates ✅ COMPLETED
- [x] Update/create README.md
- [x] Document multi-distribution support

### Phase 8: Testing & Validation ✅ COMPLETED
- [x] Syntax validation (all files compile)
- [x] Import tests (Debian imports successfully)
- [x] Configuration loading tests (Debian & Ubuntu configs load)
- [x] Arch regression tests (existing Arch config still works)
- [x] Fixed AUR/Flatpak compatibility issue (created BaseSystemRepository)

---

## Decisions Made

✅ **Question 1:** Single `Debian` class with `variant` parameter for Ubuntu  
✅ **Question 2:** Default release = `"stable"` (tracks Debian stable)  
✅ **Question 3:** Always use `dracut` for initramfs  
✅ **Question 4:** Let apt fail at runtime with clear errors (no pre-validation)

---

## File Changes Summary

| File | Status | Type | Description |
|------|--------|------|-------------|
| `src/pykod/repositories/base.py` | ✅ | Modified | Split Repository into base + BaseSystemRepository |
| `src/pykod/repositories/arch.py` | ✅ | Modified | Add `generate_initramfs()`, inherit BaseSystemRepository |
| `src/pykod/repositories/debian.py` | ✅ | New | Debian/Ubuntu implementation |
| `src/pykod/repositories/__init__.py` | ✅ | Modified | Export Debian and BaseSystemRepository |
| `src/pykod/core.py` | ✅ | Modified | Use Repository method for initramfs |
| `src/pykod/config.py` | ✅ | Modified | Use Repository method in hooks |
| `example/configuration-debian.py` | ✅ | New | Debian example |
| `example/configuration-ubuntu.py` | ✅ | New | Ubuntu example |
| `README.md` | ✅ | Modified | Multi-distro docs |

---

## Detailed Changes

### Phase 1: Repository Base Class

**File:** `src/pykod/repositories/base.py`

Add these abstract methods to the `Repository` class:

```python
from abc import ABC, abstractmethod

# Add to Repository class:
@abstractmethod
def install_base(self, mount_point: str, packages: "PackageList") -> None:
    """Install base system using distro bootstrap tool."""
    pass

@abstractmethod
def get_base_packages(self, conf) -> dict:
    """Get base packages required for this distribution."""
    pass

@abstractmethod
def get_kernel_info(self, mount_point: str, package) -> tuple[str, str]:
    """Retrieve kernel file path and version."""
    pass

@abstractmethod
def setup_linux(self, mount_point: str, kernel_package) -> str:
    """Setup kernel in boot directory."""
    pass

@abstractmethod
def generate_initramfs(self, mount_point: str, kver: str) -> None:
    """Generate initial ramdisk for kernel."""
    pass

@abstractmethod
def install_packages(self, package_name: set | list) -> str:
    """Return command to install packages."""
    pass

@abstractmethod
def remove_packages(self, packages_name: set | list) -> str:
    """Return command to remove packages."""
    pass

@abstractmethod
def update_database(self) -> str:
    """Return command to update package database."""
    pass

@abstractmethod
def update_installed_packages(self, packages: tuple) -> str:
    """Return command to upgrade installed packages."""
    pass

@abstractmethod
def is_valid_packages(self, pkgs: list) -> list:
    """Check if packages exist in repository."""
    pass
```

---

### Phase 2: Arch Implementation

**File:** `src/pykod/repositories/arch.py`

Add after `setup_linux()` method (around line 112):

```python
def generate_initramfs(self, mount_point: str, kver: str) -> None:
    """Generate initramfs using dracut (Arch's initramfs generator)."""
    exec_chroot(
        f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img",
        mount_point=mount_point
    )
```

---

### Phase 3: Core Boot Logic

**File 1:** `src/pykod/core.py` - Line 215

Change:
```python
exec_chroot(f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img")
```

To:
```python
base.generate_initramfs("/mnt", kver)
```

**File 2:** `src/pykod/config.py` - Lines 773-778

Change:
```python
exec_chroot(
    f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img",
    mount_point=mount_point,
)
```

To:
```python
conf._base.generate_initramfs(mount_point, kver)
```

---

## Testing Commands

```bash
# Syntax validation
python -m py_compile src/pykod/repositories/base.py
python -m py_compile src/pykod/repositories/arch.py
python -m py_compile src/pykod/repositories/debian.py

# Import test
python -c "from pykod.repositories import Debian; print('✓ Debian import works')"

# Configuration test
python example/configuration-debian.py --dry-run --debug

# Arch regression test
python example/configuration.py --dry-run --debug
```

---

## Rollback Procedure

If issues occur, revert in reverse order:

1. Remove `example/configuration-*.py` files
2. Revert `src/pykod/repositories/__init__.py`
3. Delete `src/pykod/repositories/debian.py`
4. Revert `src/pykod/config.py` (restore dracut call)
5. Revert `src/pykod/core.py` (restore dracut call)
6. Revert `src/pykod/repositories/arch.py` (remove generate_initramfs)
7. Revert `src/pykod/repositories/base.py` (remove abstract methods)

---

## Notes

- All changes are backward compatible
- Arch functionality remains unchanged
- Debian is additive-only (new class)
- No breaking changes to public API

---

**Last Updated:** 2025-02-07 - All phases completed successfully!

## Phase 8 Notes - Repository Architecture Fix

During testing, we discovered that making all repository methods abstract broke AUR and Flatpak, which are auxiliary package repositories that don't provide base system installation capabilities.

**Solution:** Created a two-tier inheritance hierarchy:
- `Repository` (ABC) - Base class with package management methods (install, remove, update, validate)
- `BaseSystemRepository` (extends Repository) - For distros that can bootstrap a system (Arch, Debian)
  - Adds: `install_base()`, `get_base_packages()`, `get_kernel_info()`, `setup_linux()`, `generate_initramfs()`, `update_database()`

This allows:
- Arch & Debian → inherit from `BaseSystemRepository` (full system installation)
- AUR & Flatpak → inherit from `Repository` (package management only)
