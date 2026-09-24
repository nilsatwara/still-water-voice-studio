from fastapi import APIRouter
from . import admin, admin_media, admin_pages, admin_posts, admin_taxonomy, capabilities, captcha, health, menus, settings, voices

router = APIRouter()
router.include_router(health.router)
router.include_router(capabilities.router)
router.include_router(voices.router)
router.include_router(admin.router)
router.include_router(admin_pages.router)
router.include_router(admin_posts.router)
router.include_router(admin_taxonomy.router)
router.include_router(admin_media.router)
router.include_router(settings.router)
router.include_router(menus.router)
router.include_router(captcha.router)
