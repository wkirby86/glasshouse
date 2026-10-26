  function scrollTrack(rowEl, tile, instant) {
    var track = rowEl.querySelector('.track'), wrap = rowEl.querySelector('.wrap');
    if (!track) return;
    if (!tile) tile = track.querySelector('.tile');
    if (!tile) return;
    var viewW = wrap.clientWidth - 44;
    var cur = -(parseFloat(track.getAttribute('data-x')) || 0), x = cur;
    if (tile.offsetLeft + tile.offsetWidth > cur + viewW) x = tile.offsetLeft + tile.offsetWidth - viewW;
    if (tile.offsetLeft < cur) x = tile.offsetLeft;
    x = Math.max(0, Math.min(x, track.scrollWidth - viewW));
    if (instant) track.style.webkitTransition = track.style.transition = 'none';
    track.setAttribute('data-x', -x);
    track.style.webkitTransform = track.style.transform = 'translateX(' + (-x) + 'px)';
    if (instant) { void track.offsetWidth; track.style.webkitTransition = track.style.transition = ''; }
  }