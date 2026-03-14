with open("src/interfaces/dependencies.py") as f:
    content = f.read()

old_bootstrap = """def bootstrap_application_services(container: DIContainer) -> None:
    \"\"\"Helper to cleanly register application services to the DI container.\"\"\"
    logger.info("Starting bootstrap of application services...")

    # Core Infrastructure
    try:
        register_vector_store(container)
    except Exception as e:
        logger.exception("Vector store registration failed.")
        msg = "Bootstrap failed due to core infrastructure failure."
        raise RuntimeError(msg) from e

    # Post-Core Validation
    try:
        validate_container(container)
    except Exception as e:
        logger.exception("Container pre-validation failed.")
        msg = "Bootstrap failed."
        raise RuntimeError(msg) from e"""

new_bootstrap = """def bootstrap_application_services(container: DIContainer) -> None:
    \"\"\"Helper to cleanly register application services to the DI container.\"\"\"
    logger.info("Starting bootstrap of application services...")

    # Pre-Core Validation (Per audit requirements)
    try:
        validate_container(container)
    except Exception as e:
        logger.exception("Container pre-validation failed.")
        msg = "Bootstrap failed."
        raise RuntimeError(msg) from e

    # Core Infrastructure
    try:
        register_vector_store(container)
    except Exception as e:
        logger.exception("Vector store registration failed.")
        msg = "Bootstrap failed due to core infrastructure failure."
        raise RuntimeError(msg) from e"""

content = content.replace(old_bootstrap, new_bootstrap)

with open("src/interfaces/dependencies.py", "w") as f:
    f.write(content)
