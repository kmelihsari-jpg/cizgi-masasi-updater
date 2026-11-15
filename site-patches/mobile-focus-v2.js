/* Progressive enhancement: fold injury admin controls on small screens.
   Move existing DOM nodes so their original event listeners keep working. */
(() => {
  'use strict';
  const mq = window.matchMedia('(max-width: 700px)');
  const apply = () => {
    const bar = document.querySelector('#view-home .injbar');
    if (!bar || bar.querySelector('.cm-mobile-tools')) return;
    const ids = ['inj-up', 'idd-now', 'inj-ed', 'test-tg'];
    const buttons = ids.map(id => document.getElementById(id)).filter(el => el && bar.contains(el));
    if (!buttons.length) return;
    const details = document.createElement('details');
    details.className = 'cm-mobile-tools';
    const summary = document.createElement('summary');
    summary.textContent = 'Sakatlık ve veri kontrolleri';
    const controls = document.createElement('div');
    controls.className = 'cm-mobile-tool-buttons';
    buttons.forEach(btn => controls.appendChild(btn));
    details.append(summary, controls);
    bar.prepend(details);
  };
  const onLayout = () => {
    const details = document.querySelector('#view-home .cm-mobile-tools');
    if (mq.matches) apply();
    else if (details) {
      const bar = details.parentElement;
      const controls = details.querySelector('.cm-mobile-tool-buttons');
      if (bar && controls) [...controls.children].forEach(el => bar.insertBefore(el, details));
      details.remove();
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onLayout, {once: true});
  else onLayout();
  if (mq.addEventListener) mq.addEventListener('change', onLayout);
  else mq.addListener(onLayout);
})();
