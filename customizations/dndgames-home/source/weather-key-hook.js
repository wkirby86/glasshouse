    /* DNDGAMES-HOME-FORK-V23 KEY BEGIN */
    if (!state.arranging && !recents.open && !recents.loading &&
        e.keyCode === KEY.up && state.row === nextShown(0, 1) &&
        window.DNDWeatherLocation && window.DNDWeatherLocation.focusControl()) {
      e.preventDefault();
      return;
    }
    /* DNDGAMES-HOME-FORK-V23 KEY END */
