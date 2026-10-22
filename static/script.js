
document.addEventListener("DOMContentLoaded", () => {
    // Update the footer year.
    const yearElement = document.getElementById("currentYear");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // Mobile navigation.
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", () => {
            const isOpen = navLinks.classList.toggle("open");

            menuToggle.setAttribute("aria-expanded", String(isOpen));
            menuToggle.setAttribute(
                "aria-label",
                isOpen ? "Close navigation" : "Open navigation"
            );
        });

        navLinks.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
                menuToggle.setAttribute("aria-label", "Open navigation");
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                navLinks.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
                menuToggle.setAttribute("aria-label", "Open navigation");
            }
        });
    }

    // Reveal elements as they enter the viewport.
    const animatedElements = document.querySelectorAll(".fade-up");

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(
            (entries, currentObserver) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        currentObserver.unobserve(entry.target);
                    }
                });
            },
            {
                threshold: 0.12,
                rootMargin: "0px 0px -25px 0px"
            }
        );

        animatedElements.forEach((element, index) => {
            element.style.transitionDelay = `${Math.min(index % 4, 3) * 70}ms`;
            observer.observe(element);
        });
    } else {
        animatedElements.forEach((element) => {
            element.classList.add("is-visible");
        });
    }

    // Dismiss server-generated flash messages.
    document.querySelectorAll(".flash-close").forEach((button) => {
        button.addEventListener("click", () => {
            const flash = button.closest(".flash");

            if (flash) {
                flash.remove();
            }
        });
    });
});
