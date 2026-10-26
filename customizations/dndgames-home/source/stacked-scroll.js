  function scrollTrack(rowEl, tile, instant) {
    var track = rowEl.querySelector('.track'), wrap = rowEl.querySelector('.wrap');
    if (!track) return;
    if (!tile) tile = track.querySelector('.tile');
    if (!tile) return;
    var viewW = wrap.clientWidth - 44;
    /* DNDGAMES-STACKED-V2: centre only short tracks; long tracks retain scrolling.
       Remove centring in Arrange mode so the old reorder controls stay predictable. */
    track.className = 'track';
    if (!state.arranging) {
      var all = track.querySelectorAll('.tile'), used = 0;
      for (var n = 0; n < all.length; n++) {
        var style = window.getComputedStyle ? window.getComputedStyle(all[n]) : null;
        used += all[n].offsetWidth + (style ? (parseFloat(style.marginRight) || 0) : 12);
      }
      if (used > 0 && used <= viewW) {
        track.className = 'track dnd-centered';
        track.setAttribute('data-x', 0);
        track.style.webkitTransform = track.style.transform = 'translateX(0px)';
        return;
      }
    }
    var cur = -(parseFloat(track.getAttribute('data-x')) || 0), x = cur;
    if (tile.offsetLeft + tile.offsetWidth > cur + viewW) x = tile.offsetLeft + tile.offsetWidth - viewW;
    if (tile.offsetLeft < cur) x = tile.offsetLeft;
    x = Math.max(0, Math.min(x, track.scrollWidth - viewW));
    if (instant) track.style.webkitTransition = track.style.transition = 'none';
    track.setAttribute('data-x', -x);
    track.style.webkitTransform = track.style.transform = 'translateX(' + (-x) + 'px)';
    if (instant) { void track.offsetWidth; track.style.webkitTransition = track.style.transition = ''; }
  }