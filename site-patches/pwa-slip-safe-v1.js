/* Narrow fallback for iOS versions relying on navigator.standalone.
   No event handlers are replaced and no betting/portfolio state is touched. */
(() => {
  'use strict';
  if (typeof navigator !== 'undefined' && navigator.standalone === true) {
    document.documentElement.classList.add('cm-ios-standalone');
  }
})();
