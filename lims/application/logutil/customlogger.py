import importlib
import inspect
import logging
import os
import pkgutil
import random
from typing import Any, Set

import wrapt
from django.apps import apps
from django.conf import settings
from django.db import models

from logutil.log import log

# Global state tracking
_PROJECT_ROOT_PREFIX: str = None
_MODELS_ALREADY_WRAPPED: Set[str] = set()
_CUSTOMLOGGER_BOOTSTRAPPED: bool = False
_URLS_CALLBACKS_BOOTSTRAPPED: bool = False

# Name of this module/package (used to always exclude ourselves)
_THIS_MODULE = __name__  # e.g. "logutil.customlogger"
_THIS_PACKAGE = _THIS_MODULE.split(".")[0]  # e.g. "logutil"

# --- Configuration and normalization ------------------------------------------------

CUSTOMLOGGER_ENABLED: bool = getattr(settings, "CUSTOMLOGGER_ENABLED", True)
CUSTOMLOGGER_SAMPLE_RATE: float = float(getattr(settings, "CUSTOMLOGGER_SAMPLE_RATE", 1.0))
CUSTOMLOGGER_LOG_LEVEL: str = str(
    getattr(settings, "CUSTOMLOGGER_LOG_LEVEL", "DEBUG" if settings.DEBUG else "INFO")
).upper()

# Normalize exclude prefixes from settings into a set of stable prefixes (always end with '.')
_raw_excludes = getattr(settings, "CUSTOMLOGGER_EXCLUDE_MODULES", [
    'django.',
    'django.contrib.',
    'django.db.',
    'django.utils.',
    'django.core.',
    'rest_framework.',
    'auditlog.',
    'debug_toolbar.',
    'corsheaders.',
    'jazzmin.',
])

CUSTOMLOGGER_EXCLUDE_MODULES: Set[str] = set()
for p in _raw_excludes:
    p = str(p)
    if p and not p.endswith("."):
        CUSTOMLOGGER_EXCLUDE_MODULES.add(p + ".")
    else:
        CUSTOMLOGGER_EXCLUDE_MODULES.add(p)

# **Defensive:** always exclude this customlogger module and package even if user forgot.
CUSTOMLOGGER_EXCLUDE_MODULES.add(_THIS_PACKAGE + ".")
CUSTOMLOGGER_EXCLUDE_MODULES.add(_THIS_MODULE + ".")
CUSTOMLOGGER_EXCLUDE_MODULES.add(_THIS_PACKAGE)
CUSTOMLOGGER_EXCLUDE_MODULES.add(_THIS_MODULE)

# Build allowed prefixes from INSTALLED_APPS + optional APPLICATION_NAME
_ALLOWED_MODULE_PREFIXES: Set[str] = set()

# Add APPLICATION_NAME if present (normalize)
_proj_prefix = getattr(settings, "APPLICATION_NAME", None)
if _proj_prefix:
    _proj_prefix = str(_proj_prefix)
    if not _proj_prefix.endswith("."):
        _ALLOWED_MODULE_PREFIXES.add(_proj_prefix + ".")
        _ALLOWED_MODULE_PREFIXES.add(_proj_prefix)
    else:
        _ALLOWED_MODULE_PREFIXES.add(_proj_prefix)
        _ALLOWED_MODULE_PREFIXES.add(_proj_prefix.rstrip("."))

# Add entries derived from INSTALLED_APPS
for app_path in getattr(settings, "INSTALLED_APPS", []):
    try:
        app_path = str(app_path)
    except Exception:
        continue
    if not app_path:
        continue
    # Add full dotted path (with trailing dot) and top-level package
    if not app_path.endswith("."):
        _ALLOWED_MODULE_PREFIXES.add(app_path + ".")
    else:
        _ALLOWED_MODULE_PREFIXES.add(app_path)
    top_level = app_path.split(".")[0]
    if top_level:
        _ALLOWED_MODULE_PREFIXES.add(top_level + ".")
        _ALLOWED_MODULE_PREFIXES.add(top_level)


# --- Helpers -----------------------------------------------------------------------

def _get_log_level_int() -> int:
    """Convert log level string to logging module constant."""
    return getattr(logging, CUSTOMLOGGER_LOG_LEVEL, logging.DEBUG)


def _is_wrapped(obj: Any) -> bool:
    """Check if an object has already been wrapped."""
    return getattr(obj, "__customlogger_wrapped__", False)


def _mark_wrapped(obj: Any) -> None:
    """Mark an object as wrapped to prevent duplicate wrapping."""
    try:
        setattr(obj, "__customlogger_wrapped__", True)
    except (AttributeError, TypeError):
        pass


def should_log() -> bool:
    """Determine if we should log based on sample rate."""
    return random.random() <= CUSTOMLOGGER_SAMPLE_RATE


def _module_allowed(module_name: str) -> bool:
    """Decide whether to allow wrapping for a given module name.

    Rules:
      1) If module is empty -> disallow.
      2) If module starts with any excluded prefix -> disallow.
      3) If module starts with any allowed prefix -> allow.
      4) Otherwise -> disallow (conservative).
    """
    global _PROJECT_ROOT_PREFIX

    if _PROJECT_ROOT_PREFIX is None:
        _PROJECT_ROOT_PREFIX = getattr(settings, "APPLICATION_NAME", "application")

    if not module_name:
        return False

    # Always exclude Django core
    if module_name.startswith("django."):
        return False

    # Always exclude customlogger & internals (defensive; ensures we don't wrap our own helpers)
    if module_name == _THIS_MODULE or module_name.startswith(_THIS_MODULE + "."):
        return False
    if module_name == _THIS_PACKAGE or module_name.startswith(_THIS_PACKAGE + "."):
        return False

    # Explicit excludes (from settings + forced ones)
    for excluded_prefix in CUSTOMLOGGER_EXCLUDE_MODULES:
        if module_name.startswith(excluded_prefix):
            return False

    # If module matches any of the allowed app prefixes, allow it
    for allowed in _ALLOWED_MODULE_PREFIXES:
        if module_name == allowed.rstrip(".") or module_name.startswith(allowed):
            return True

    # Conservative default: disallow
    return False


def log_wrap(wrapped, instance, args, kwargs):
    """Core wrapper function that logs start/end of method calls."""
    # Defensive: if the wrapped function itself is in our module, never wrap it (safety belt)
    wrapped_mod = getattr(wrapped, "__module__", "")
    if wrapped_mod == _THIS_MODULE or wrapped_mod.startswith(_THIS_MODULE + "."):
        # Call original directly (do not attempt to log) to avoid self-recursion
        return wrapped(*args, **kwargs)

    if not CUSTOMLOGGER_ENABLED or not should_log():
        return wrapped(*args, **kwargs)

    orig_module = wrapped_mod
    orig_qname = getattr(wrapped, "__qualname__", getattr(wrapped, "__name__", str(wrapped)))
    func_name = f"{orig_module}.{orig_qname}"
    level = _get_log_level_int()

    if log.isEnabledFor(level):
        log.log(level, "[START] %s ", func_name)

    try:
        result = wrapped(*args, **kwargs)

        if inspect.isawaitable(result):
            async def _async_tracer():
                res = await result
                if log.isEnabledFor(level):
                    log.log(level, "[END] %s ", func_name)
                return res

            return _async_tracer()
        else:
            if log.isEnabledFor(level):
                log.log(level, "[END] %s ", func_name)
            return result
    except Exception:
        log.exception("[ERROR] %s raised an exception", func_name)
        raise


def wrap_model_methods(model: models.Model) -> None:
    """Specialized wrapper for Django model methods.

    Conservative behavior:
      - Skip nested classes (including exception classes like DoesNotExist).
      - Only wrap bona-fide functions / methods / method-descriptors.
      - Never wrap anything from the customlogger package itself.
    """
    model_name = f"{model.__module__}.{model.__name__}"
    if model_name in _MODELS_ALREADY_WRAPPED:
        return

    _MODELS_ALREADY_WRAPPED.add(model_name)
    log.debug(f"Wrapping model (candidate): {model_name}")

    # Methods we never want to wrap (Django internals / dangerous)
    SKIP_ATTRS = {
        'clean', 'validate_unique', 'delete', 'save_base', 'get_deferred_fields',
        'prepare_database_save', 'get_next_by_created_dt', 'get_previous_by_created_dt',
        'from_db', 'refresh_from_db', 'full_clean', '__init_subclass__',
    }

    for attr_name in dir(model):
        if attr_name.startswith('_'):
            continue

        if attr_name in SKIP_ATTRS:
            log.debug(f"Skipping attribute by name: {model_name}.{attr_name}")
            continue

        try:
            attr = getattr(model, attr_name)
        except Exception:
            # attribute access can raise in some descriptors — skip defensively
            continue

        # NEVER wrap classes (this prevents replacing nested exception classes)
        if inspect.isclass(attr):
            log.debug(f"Skipping class attribute: {model_name}.{attr_name} (is class)")
            continue

        # Unwrap decorated descriptors to find the real underlying callable
        func_obj = getattr(attr, "__func__", getattr(attr, "__wrapped__", attr))

        # If underlying is a class (defensive), skip
        if inspect.isclass(func_obj):
            log.debug(f"Skipping attribute whose underlying is a class: {model_name}.{attr_name}")
            continue

        # Only wrap if underlying is a function, a method, or method-descriptor
        if not (inspect.isfunction(func_obj) or inspect.ismethod(func_obj) or inspect.ismethoddescriptor(func_obj)):
            log.debug(f"Skipping non-function attribute: {model_name}.{attr_name} (type={type(attr)})")
            continue

        # Defensive: don't wrap exception classes if any slipped through
        try:
            if isinstance(attr, type) and issubclass(attr, BaseException):
                log.debug(f"Skipping exception class attribute: {model_name}.{attr_name}")
                continue
        except Exception:
            # If issubclass check itself fails, be conservative and skip wrapping
            log.debug(f"Skipping attribute due to issubclass check failure: {model_name}.{attr_name}")
            continue

        if _is_wrapped(attr):
            continue

        # Determine module where attribute originally defined
        attr_module = getattr(func_obj, "__module__", "")

        # Defensive: never wrap functions defined in the customlogger module/package
        if attr_module == _THIS_MODULE or attr_module.startswith(_THIS_MODULE + "."):
            log.debug(f"Skipping customlogger-internal attribute: {model_name}.{attr_name} -> {attr_module}")
            continue
        if attr_module == _THIS_PACKAGE or attr_module.startswith(_THIS_PACKAGE + "."):
            log.debug(f"Skipping customlogger-package attribute: {model_name}.{attr_name} -> {attr_module}")
            continue

        # If attribute is defined in a disallowed module, skip it
        if not _module_allowed(attr_module):
            log.debug(f"Skipping wrap of {model_name}.{attr_name} — module disallowed: {attr_module}")
            continue

        # Wrap it
        try:
            wrapped = wrapt.FunctionWrapper(attr, log_wrap)
            _mark_wrapped(wrapped)
            setattr(model, attr_name, wrapped)
            log.debug(f"Wrapped model method: {model_name}.{attr_name}")
        except Exception as e:
            log.debug(f"Failed to wrap {model_name}.{attr_name}: {e}")


def wrap_class_methods(cls) -> None:
    """Wrap methods of a class including classmethods and staticmethods.

    Conservative:
      - Skip nested classes (including exception classes).
      - Only wrap actual function objects, classmethod.__func__, or staticmethod.__func__.
      - Avoid wrapping classes defined in customlogger/package.
    """
    cls_mod = getattr(cls, "__module__", "")
    if not _module_allowed(cls_mod):
        log.debug(f"Skipping class wrapping for {getattr(cls, '__name__', str(cls))} — module {cls_mod} not allowed")
        return

    # Defensive: avoid wrapping classes defined in customlogger/package
    if cls_mod == _THIS_MODULE or cls_mod.startswith(_THIS_MODULE + "."):
        log.debug(f"Skipping class {cls.__name__} because it's in customlogger module")
        return
    if cls_mod == _THIS_PACKAGE or cls_mod.startswith(_THIS_PACKAGE + "."):
        log.debug(f"Skipping class {cls.__name__} because it's in customlogger package")
        return

    for name, val in cls.__dict__.items():
        if name.startswith("__"):
            continue

        # Skip nested classes entirely
        if inspect.isclass(val):
            log.debug(f"Skipping nested class attribute on {cls.__name__}: {name}")
            continue

        try:
            # classmethod: wrap the underlying function
            if isinstance(val, classmethod):
                func = val.__func__
                func_mod = getattr(func, "__module__", "")
                if not _is_wrapped(func) and _module_allowed(func_mod) and not (
                        func_mod == _THIS_MODULE or func_mod.startswith(_THIS_MODULE + ".")):
                    wrapped = wrapt.FunctionWrapper(func, log_wrap)
                    _mark_wrapped(wrapped)
                    setattr(cls, name, classmethod(wrapped))

            # staticmethod: wrap the underlying function
            elif isinstance(val, staticmethod):
                func = val.__func__
                func_mod = getattr(func, "__module__", "")
                if not _is_wrapped(func) and _module_allowed(func_mod) and not (
                        func_mod == _THIS_MODULE or func_mod.startswith(_THIS_MODULE + ".")):
                    wrapped = wrapt.FunctionWrapper(func, log_wrap)
                    _mark_wrapped(wrapped)
                    setattr(cls, name, staticmethod(wrapped))

            # plain function defined on the class
            elif inspect.isfunction(val):
                func_mod = getattr(val, "__module__", "")
                if not _is_wrapped(val) and _module_allowed(func_mod) and not (
                        func_mod == _THIS_MODULE or func_mod.startswith(_THIS_MODULE + ".")):
                    wrapped = wrapt.FunctionWrapper(val, log_wrap)
                    _mark_wrapped(wrapped)
                    setattr(cls, name, wrapped)

        except Exception as e:
            log.debug(f"Failed to wrap {getattr(cls, '__name__', str(cls))}.{name}: {e}")


def is_django_internal(obj) -> bool:
    """Check if an object is part of Django's internals or explicitly excluded modules."""
    module = getattr(obj, '__module__', '')
    if not module:
        return False
    if module.startswith('django.'):
        return True
    return any(module.startswith(excl) for excl in CUSTOMLOGGER_EXCLUDE_MODULES)


def wrap_module_functions(module) -> None:
    """Wrap functions and classes in a module if the module is allowed.

    Conservative behavior:
      - Do not wrap the customlogger package/module itself.
      - Only wrap module-level functions (where underlying.__module__ == module.__name__).
      - For classes defined in the module, call wrap_class_methods on the class (not replacing the class).
      - Skip properties, descriptors and nested classes.
    """
    mod_name = getattr(module, "__name__", "")

    # Defensive: never attempt to wrap customlogger module/package
    if mod_name == _THIS_MODULE or mod_name.startswith(_THIS_MODULE + "."):
        log.debug(f"Not wrapping module (customlogger): {mod_name}")
        return
    if mod_name == _THIS_PACKAGE or mod_name.startswith(_THIS_PACKAGE + "."):
        log.debug(f"Not wrapping module (customlogger package): {mod_name}")
        return

    if not _module_allowed(mod_name):
        log.debug(f"Module not allowed for wrapping: {mod_name}")
        return

    for attr_name in dir(module):
        # Skip Python internals
        if attr_name.startswith("__") and attr_name.endswith("__"):
            continue

        try:
            attr = getattr(module, attr_name)
        except Exception:
            continue

        # Try to get the underlying function/class if decorated
        underlying = getattr(attr, "__func__", getattr(attr, "__wrapped__", attr))

        # If underlying is a class that was defined in the same module, wrap its methods
        try:
            if inspect.isclass(underlying) and getattr(underlying, "__module__", "") == mod_name:
                # Don't attempt to wrap classes that are part of customlogger itself
                if getattr(underlying, "__module__", "").startswith(_THIS_PACKAGE):
                    log.debug(f"Skipping wrap_class_methods for customlogger class: {mod_name}.{attr_name}")
                else:
                    try:
                        wrap_class_methods(underlying)
                        log.debug(f"Wrapped class methods for: {mod_name}.{attr_name}")
                    except Exception as e:
                        log.debug(f"Failed wrap_class_methods for {mod_name}.{attr_name}: {e}")
                continue
        except Exception:
            # Defensive: if inspect or module check fails — skip this attribute
            continue

        # Only wrap bona-fide functions/methods defined in this module
        try:
            underlying_mod = getattr(underlying, "__module__", "")
            if (inspect.isfunction(underlying) or inspect.ismethod(underlying)) and underlying_mod == mod_name:
                # Avoid wrapping customlogger internals
                if underlying_mod == _THIS_MODULE or underlying_mod.startswith(_THIS_MODULE + "."):
                    log.debug(f"Skipping wrapping internal function: {mod_name}.{attr_name} -> {underlying_mod}")
                    continue

                # Defensive: ensure attribute not already marked wrapped
                if _is_wrapped(attr):
                    continue

                # Ensure module allowed for the underlying function
                if not _module_allowed(underlying_mod):
                    log.debug(
                        f"Skipping wrap of {mod_name}.{attr_name} — underlying module disallowed: {underlying_mod}")
                    continue

                try:
                    wrapped = wrapt.FunctionWrapper(attr, log_wrap)
                    _mark_wrapped(wrapped)
                    setattr(module, attr_name, wrapped)
                    log.debug(f"Wrapped function: {mod_name}.{attr_name}")
                except Exception as e:
                    log.debug(f"Failed to wrap function {mod_name}.{attr_name}: {e}")
        except Exception as e:
            log.debug(f"Error evaluating/wrapping {mod_name}.{attr_name}: {e}")
            continue


def custom_wrap_project_apps() -> None:
    """Main entry that discovers and wraps project code.

    Uses pkgutil to import submodules of installed apps so lazily-imported modules
    (like ajax view modules) get imported and wrapped at startup.
    """
    global _CUSTOMLOGGER_BOOTSTRAPPED

    if _CUSTOMLOGGER_BOOTSTRAPPED:
        return

    if os.environ.get("RUN_MAIN") not in (None, "true", "1"):
        log.debug("custom_wrap skipped: not running in main/reloader child process.")
        return

    log.info("[CUSTOMLOGGER] Initializing method call logging")
    log.debug(f"[CUSTOMLOGGER] Excluded prefixes: {sorted(CUSTOMLOGGER_EXCLUDE_MODULES)}")
    log.debug(
        f"[CUSTOMLOGGER] Allowed prefixes derived from INSTALLED_APPS/APPLICATION_NAME: {sorted(_ALLOWED_MODULE_PREFIXES)}")

    # 1. Wrap all registered models (safe-wrap allowed attributes only)
    try:
        for model in apps.get_models():
            try:
                wrap_model_methods(model)
            except Exception as e:
                log.debug(f"Failed to wrap model {model.__name__}: {e}")
    except Exception as e:
        log.warning(f"Failed to wrap models: {e}")

    # 2. Import and wrap modules by app package (more reliable than os.walk)
    for app_config in apps.get_app_configs():
        try:
            package = importlib.import_module(app_config.name)
        except Exception as e:
            log.debug(f"Could not import app package {app_config.name}: {e}")
            continue

        # If the package has a __path__, walk submodules
        if hasattr(package, "__path__"):
            try:
                for finder, submod_name, ispkg in pkgutil.walk_packages(package.__path__, prefix=app_config.name + "."):
                    # Skip clearly excluded names early
                    if any(submod_name.startswith(p) for p in CUSTOMLOGGER_EXCLUDE_MODULES):
                        log.debug(f"Skipping excluded submodule: {submod_name}")
                        continue
                    try:
                        submod = importlib.import_module(submod_name)
                        wrap_module_functions(submod)
                    except Exception as e:
                        log.debug(f"Failed to import/wrap {submod_name}: {e}")
            except Exception as e:
                log.debug(f"pkgutil.walk_packages failed for {app_config.name}: {e}")
        else:
            # single-file app package: just wrap the package module itself
            try:
                wrap_module_functions(package)
            except Exception as e:
                log.debug(f"Failed to wrap package {app_config.name}: {e}")

    # ---- Sanity check: ensure no model exception attributes were accidentally corrupted ----
    try:
        import inspect
        bad = []
        for model in apps.get_models():
            model_name = f"{model.__module__}.{model.__name__}"
            for name in ("DoesNotExist", "MultipleObjectsReturned"):
                if hasattr(model, name):
                    val = getattr(model, name)
                    try:
                        ok = inspect.isclass(val) and issubclass(val, BaseException)
                    except Exception:
                        ok = False
                    if not ok:
                        bad.append((model_name, name, repr(val)))

        if bad:
            # Log up to first 20 problematic entries for visibility
            log.error("[CUSTOMLOGGER] Detected corrupted model exception attributes after wrapping: %s", bad[:20])

            # If running in DEBUG mode, raise to fail fast so you catch the bug during dev.
            # Use settings.DEBUG to avoid crashing production unintentionally.
            try:
                if getattr(settings, "DEBUG", False):
                    raise RuntimeError("customlogger corrupted model exception attributes. See logs for details.")
            except Exception:
                # If settings not available for some reason, don't crash — still log
                pass
    except Exception as e:
        # Do not allow the sanity-check to break startup; just log the failure
        log.warning(f"[CUSTOMLOGGER] Sanity-check failed: {e}")
    # --------------------------------------------------------------------------------------

    _CUSTOMLOGGER_BOOTSTRAPPED = True
    log.info("[CUSTOMLOGGER] Completed method call logging setup")
