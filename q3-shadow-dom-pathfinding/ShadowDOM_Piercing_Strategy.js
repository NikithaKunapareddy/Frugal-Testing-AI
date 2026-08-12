/**
 * Resilient Shadow DOM Piercing Strategy (JavaScript Implementation)
 * 
 * Problem: 
 * Standard `element.shadowRoot` queries return `null` when a shadow boundary is 
 * declared as `mode: 'closed'`. Additionally, LLMs relying on dynamic obfuscated classes
 * (like `obfuscated_v4_x89a`) cannot use static CSS selectors.
 * 
 * Solution:
 * We execute a JavaScript initialization script *before* the application loads
 * (e.g., using Playwright's `page.add_init_script()`). This script hijacks the 
 * native `Element.prototype.attachShadow` method. Whenever the application attempts 
 * to create a shadow root (open OR closed), we intercept the call, execute the native 
 * creation, and store a permanent reference to that shadow root in an exposed Array 
 * or WeakMap.
 * 
 * Automated testing frameworks can then iterate over `window._capturedShadowRoots` 
 * to perform deep querying, completely bypassing the "closed" restriction and 
 * ignoring obfuscated parent classes.
 */

(function() {
    // Array to hold references to all shadow roots (open and closed)
    window._capturedShadowRoots = [];
    
    // Store original native method
    const originalAttachShadow = Element.prototype.attachShadow;

    // Override the native method
    Element.prototype.attachShadow = function(options) {
        // Execute the native creation
        const shadowRoot = originalAttachShadow.call(this, options);
        
        // Push reference to our global array
        window._capturedShadowRoots.push(shadowRoot);
        
        return shadowRoot;
    };

    /**
     * Helper function exposed to testing frameworks to pierce the tree.
     * @param {string} selector - The CSS or property to find.
     * @returns {Element|null} - The target element if found.
     */
    window.findInAnyShadow = function(selector) {
        for (const root of window._capturedShadowRoots) {
            const el = root.querySelector(selector);
            if (el) return el;
        }
        return null;
    };
})();
