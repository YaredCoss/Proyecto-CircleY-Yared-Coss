document.addEventListener('DOMContentLoaded', () => {
    /* --- Toggle del menú responsive --- */
    const menuBtn = document.getElementById('menu-btn');
    const menu = document.getElementById('menu');
    if (menuBtn && menu) {
        menuBtn.addEventListener('click', () => {
            menu.classList.toggle('visible');
        });
    }

    /* --- Auto-cierre de mensajes flash --- */
    document.querySelectorAll('.alerta').forEach(msg => {
        setTimeout(() => msg.classList.add('fade-out'), 4500);
    });

    /* --- Submenús de navegación (categorías, etc.) --- */
    const navSubmenus = document.querySelectorAll('.submenu');
    navSubmenus.forEach(menuItem => {
        const trigger = menuItem.querySelector('.submenu-trigger') || menuItem.querySelector('span');
        if (!trigger) return;

        trigger.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();

            navSubmenus.forEach(other => {
                if (other !== menuItem) other.classList.remove('open');
            });
            menuItem.classList.toggle('open');
        });
    });

    /* --- Menú del usuario --- */
    const userMenus = document.querySelectorAll('.usuario-menu, .usuario');
    userMenus.forEach(menuItem => {
        const trigger = menuItem.querySelector('.usuario-btn');
        if (!trigger) return;

        trigger.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();

            userMenus.forEach(other => {
                if (other !== menuItem) other.classList.remove('open');
            });
            menuItem.classList.toggle('open');
        });
    });

    /* --- Cerrar menús al clicar fuera --- */
    document.addEventListener('click', () => {
        navSubmenus.forEach(menuItem => menuItem.classList.remove('open'));
        userMenus.forEach(menuItem => menuItem.classList.remove('open'));
    });
});