# Browser-tool replay helper: call run(page, fixture, accounts) with isolated fixture and credentials from memory.
async def run(page, fixture, accounts):
    from urllib.parse import urlsplit
    from playwright.async_api import expect
    base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
    errors = []
    layout_failures = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('dialog', lambda dialog: dialog.accept())
    pdf = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF'

    async def login(email, password, destination):
        await page.context.clear_cookies()
        await page.goto(base + '/auth?mode=login')
        await page.get_by_test_id('login-email-input').fill(email)
        await page.get_by_test_id('login-password-input').fill(password)
        await page.get_by_test_id('login-submit-button').click(force=True)
        await page.wait_for_url('**/' + destination, timeout=15000)

    async def check_layout(label):
        await page.wait_for_timeout(150)
        overflow = await page.evaluate('document.documentElement.scrollWidth > innerWidth')
        if overflow:
            layout_failures.append(label)
        print('FAIL layout' if overflow else 'PASS layout', label)

    try:
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        await login(fixture['team_email'], fixture['team_password'], 'dashboard')
        await page.get_by_test_id('participant-tab-project').click(force=True)
        for tid, value in [('project-title-input', 'TEST Browser collaborative project'), ('project-description-input', 'TEST leader created this project draft for activated member collaboration.'), ('project-github-input', 'https://github.com/example/test'), ('project-demo-input', 'https://example.com/demo'), ('project-video-input', 'https://example.com/video')]:
            await page.get_by_test_id(tid).fill(value)
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me') and r.request.method == 'PUT') as saved:
            await page.get_by_test_id('project-save-button').click(force=True)
        result = await saved.value
        assert result.status == 200
        submission = await result.json()
        sid = submission['submission_id']
        await expect(page.get_by_test_id('project-status')).to_have_text('draft')
        print('PASS leader saved browser draft')

        await login(fixture['member_email'], fixture['member_password'], 'dashboard')
        await page.get_by_test_id('participant-tab-project').click(force=True)
        await expect(page.get_by_test_id('project-title-input')).to_have_value('TEST Browser collaborative project')
        await page.get_by_test_id('project-description-input').fill('TEST member independently edited the project draft started by the team leader.')
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me') and r.request.method == 'PUT'):
            await page.get_by_test_id('project-save-button').click(force=True)
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me/presentation')) as uploaded:
            await page.get_by_test_id('project-presentation-file-input').set_input_files({'name':'TEST_browser_presentation.pdf','mimeType':'application/pdf','buffer':pdf})
        assert (await uploaded.value).status == 200
        await expect(page.get_by_test_id('project-presentation-download')).to_be_visible()
        print('PASS member shared draft edit and required upload')

        for tid, value in [('project-resource-title-input','TEST Browser Link'), ('project-resource-url-input','https://example.com/resource'), ('project-resource-description-input','TEST custom link description')]:
            await page.get_by_test_id(tid).fill(value)
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me/resources/link')) as link_result:
            await page.get_by_test_id('project-add-link-button').click(force=True)
        link = await (await link_result.value).json()
        await expect(page.get_by_test_id('project-resource-' + link['resource_id'])).to_be_visible()
        await page.get_by_test_id('project-file-resource-title-input').fill('TEST Browser File')
        await page.get_by_test_id('project-file-resource-description-input').fill('TEST custom supporting file description')
        await page.get_by_test_id('project-resource-file-input').set_input_files({'name':'TEST_browser_resource.pdf','mimeType':'application/pdf','buffer':pdf})
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me/resources/file')) as file_result:
            await page.get_by_test_id('project-file-resource-submit-button').click(force=True)
        file = await (await file_result.value).json()
        await expect(page.get_by_test_id('project-resource-' + file['resource_id'])).to_be_visible()
        async with page.expect_download() as download:
            await page.get_by_test_id('project-resource-download-' + file['resource_id']).click(force=True)
        assert (await download.value).suggested_filename == 'TEST_browser_resource.pdf'
        print('PASS custom optional link/file creation and private download')
        for resource in [link, file]:
            await page.get_by_test_id('project-resource-remove-' + resource['resource_id']).click(force=True)
            await expect(page.get_by_test_id('project-resource-' + resource['resource_id'])).to_have_count(0)
        print('PASS member removes optional file and link')

        # Re-add review resources through the same working browser controls.
        await page.get_by_test_id('project-resource-title-input').fill('TEST Reviewer Link')
        await page.get_by_test_id('project-resource-url-input').fill('https://example.com/review-resource')
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me/resources/link')) as link_result:
            await page.get_by_test_id('project-add-link-button').click(force=True)
        link = await (await link_result.value).json()
        await page.get_by_test_id('project-file-resource-title-input').fill('TEST Reviewer File')
        await page.get_by_test_id('project-resource-file-input').set_input_files({'name':'TEST_browser_resource.pdf','mimeType':'application/pdf','buffer':pdf})
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me/resources/file')) as file_result:
            await page.get_by_test_id('project-file-resource-submit-button').click(force=True)
        file = await (await file_result.value).json()
        await expect(page.get_by_test_id('project-resource-' + file['resource_id'])).to_be_visible()
        await page.get_by_test_id('project-final-submit-button').click(force=True)
        await expect(page.get_by_test_id('project-status')).to_have_text('submitted')
        assert await page.get_by_test_id('project-title-input').is_disabled()
        assert await page.get_by_test_id('project-save-button').count() == 0
        assert await page.locator('[data-testid^="project-resource-remove-"]').count() == 0
        print('PASS member finalizes and UI locks edits')
        await page.set_viewport_size({'width':390,'height':844})
        await check_layout('participant project mobile')
        await page.screenshot(path='/app/test_reports/browser_new_requirements/member_mobile.jpeg', quality=40, full_page=False)

        await page.set_viewport_size({'width':1920,'height':1080})
        await login(accounts['admin'][0], accounts['admin'][1], 'admin')
        await page.get_by_test_id('admin-tab-projects').click(force=True)
        await expect(page.get_by_test_id('admin-project-' + sid)).to_be_visible()
        assert await page.get_by_test_id('admin-project-video-' + sid).get_attribute('href') == 'https://example.com/video'
        assert await page.get_by_test_id('admin-resource-link-' + link['resource_id']).get_attribute('href') == 'https://example.com/review-resource'
        async with page.expect_download():
            await page.get_by_test_id('admin-resource-file-' + file['resource_id']).click(force=True)
        await page.get_by_test_id('admin-project-reopen-' + sid).click(force=True)
        await expect(page.get_by_test_id('admin-project-reopen-' + sid)).to_have_count(0)
        await page.get_by_test_id('admin-project-history-' + sid).locator('summary').click(force=True)
        await expect(page.get_by_test_id('admin-project-history-' + sid)).to_contain_text('reopened by admin')
        print('PASS admin resources, private download and audited UI reopen')

        await page.get_by_test_id('admin-tab-topics').click(force=True)
        articles = page.locator('[data-testid^="admin-topic-"]').filter(has=page.locator('button[data-testid^="admin-topic-up-"]'))
        original = await articles.evaluate_all('(els) => els.map(e => e.dataset.testid)')
        assert len(original) == 6
        first_id = original[0].replace('admin-topic-', '')
        async with page.expect_response(lambda r: r.url.endswith('/api/admin/topics/order')):
            await page.get_by_test_id('admin-topic-down-' + first_id).click(force=True)
        await expect(articles.nth(1)).to_have_attribute('data-testid', original[0])
        async with page.expect_response(lambda r: r.url.endswith('/api/admin/topics/order')):
            await page.get_by_test_id('admin-topic-up-' + first_id).click(force=True)
        await expect(articles.nth(0)).to_have_attribute('data-testid', original[0])
        assert await articles.count() == 6
        print('PASS topic down/up restores all six records')

        await page.get_by_test_id('admin-tab-notifications').click(force=True)
        nid = fixture['registration_confirmed_notice']
        notice = page.get_by_test_id('admin-notification-' + nid)
        await expect(notice).to_contain_text(fixture['team_email'])
        await expect(notice).to_contain_text('Dashboard recorded')
        await expect(notice).to_contain_text('email failed')
        assert await page.get_by_test_id('admin-notification-retry-' + fixture['member_activation_notice']).count() == 0
        async with page.expect_response(lambda r: r.url.endswith('/api/admin/notifications/' + nid + '/retry')) as retry_result:
            await page.get_by_test_id('admin-notification-retry-' + nid).click(force=True)
        retry = await retry_result.value
        assert retry.status == 200
        print('PASS recipient/dashboard/email status and eligible retry:', await retry.json())
        await page.set_viewport_size({'width':390,'height':844})
        await check_layout('admin notifications mobile')
        await page.screenshot(path='/app/test_reports/browser_new_requirements/admin_notices_mobile.jpeg', quality=40, full_page=False)

        await page.set_viewport_size({'width':1920,'height':1080})
        await login(fixture['member_email'], fixture['member_password'], 'dashboard')
        await page.get_by_test_id('participant-tab-project').click(force=True)
        await expect(page.get_by_test_id('project-status')).to_have_text('draft')
        await page.get_by_test_id('project-title-input').fill('TEST Browser reopened by admin')
        async with page.expect_response(lambda r: r.url.endswith('/api/projects/me') and r.request.method == 'PUT'):
            await page.get_by_test_id('project-save-button').click(force=True)
        await page.get_by_test_id('project-final-submit-button').click(force=True)
        await expect(page.get_by_test_id('project-status')).to_have_text('submitted')
        print('PASS member edits after reopen and finalizes again')

        await login(accounts['judge'][0], accounts['judge'][1], 'judge')
        await page.get_by_test_id('judge-team-' + fixture['team_id']).click(force=True)
        await expect(page.get_by_test_id('judge-project-title')).to_have_text('TEST Browser reopened by admin')
        assert await page.get_by_test_id('judge-video-link').get_attribute('href') == 'https://example.com/video'
        assert await page.get_by_test_id('judge-resource-link-' + link['resource_id']).get_attribute('href') == 'https://example.com/review-resource'
        async with page.expect_download():
            await page.get_by_test_id('judge-resource-file-' + file['resource_id']).click(force=True)
        print('PASS assigned judge video/link/private supporting file')
        await page.set_viewport_size({'width':390,'height':844})
        await check_layout('judge mobile')
        await page.screenshot(path='/app/test_reports/browser_new_requirements/judge_mobile.jpeg', quality=40, full_page=False)
        error_text = await page.evaluate("""() => {
            const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
            return errorElements.map(el => el.textContent).join(', ');
        }""")
        print('Found error message: ' + error_text if error_text else 'No error messages found on the page')
        print('PAGE ERRORS:', errors)
        assert not errors
        assert not layout_failures, 'Horizontal overflow: ' + ', '.join(layout_failures)
        print('PASS completed browser workflow')
    except Exception as error:
        print('FAIL browser workflow:', str(error))
        print('PAGE ERRORS:', errors)
        raise


async def check_public_routes(page):
    from urllib.parse import urlsplit
    from playwright.async_api import expect
    base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        await page.context.clear_cookies()
        await page.goto(base)
        await page.wait_for_timeout(6500)
        await expect(page.get_by_test_id('landing-page')).to_be_visible()
        assert await page.locator('[data-testid^="track-card-"]').count() == 6
        for size in [{'width':1920,'height':1080}, {'width':390,'height':844}, {'width':768,'height':1024}]:
            await page.set_viewport_size(size)
            assert not await page.evaluate('document.documentElement.scrollWidth > innerWidth')
        await page.set_viewport_size({'width':390,'height':844})
        for path, tid in [('/auth?mode=login','login-form'), ('/auth?mode=register','register-form'), ('/forgot-password','forgot-password-form'), ('/arena','arena-public-intro')]:
            await page.goto(base + path)
            await expect(page.get_by_test_id(tid)).to_be_visible()
            assert not await page.evaluate('document.documentElement.scrollWidth > innerWidth')
            print('PASS public route:', path)
        for path in ['/admin', '/judge']:
            await page.goto(base + path)
            await page.wait_for_url('**/auth?mode=login')
            print('PASS unauthorized route protected:', path)
        assert not errors, errors
    except Exception as e:
        print('FAIL public route regression:', str(e))
        raise


async def check_topic_order_sync(page, admin):
    from urllib.parse import urlsplit
    from playwright.async_api import expect
    base = urlsplit(page.url).scheme + '://' + urlsplit(page.url).netloc
    original = None
    try:
        await page.context.clear_cookies()
        await page.goto(base + '/auth?mode=login')
        await page.get_by_test_id('login-email-input').fill(admin[0])
        await page.get_by_test_id('login-password-input').fill(admin[1])
        await page.get_by_test_id('login-submit-button').click(force=True)
        await page.wait_for_url('**/admin')
        await page.get_by_test_id('admin-tab-topics').click(force=True)
        original = await page.locator('article[data-testid^="admin-topic-"]').evaluate_all('(els)=>els.map(el=>el.dataset.testid.replace("admin-topic-",""))')
        async with page.expect_response(lambda r: r.url.endswith('/api/admin/topics/order')):
            await page.get_by_test_id('admin-topic-down-' + original[0]).click(force=True)
        await expect(page.locator('article[data-testid^="admin-topic-"]').nth(0)).to_have_attribute('data-testid','admin-topic-' + original[1])
        await page.get_by_test_id('dash-logo-link').click(force=True)
        await expect(page.get_by_test_id('landing-page')).to_be_visible()
        await page.wait_for_timeout(6500)
        displayed = await page.locator('[data-testid^="track-card-"]').evaluate_all('(els)=>els.map(el=>el.dataset.testid.replace("track-card-",""))')
        public = await (await page.request.get(base + '/api/public/meta')).json()
        saved = [x['topic_id'] for x in public['topics']]
        assert displayed == saved, f'Stale SPA topic order {displayed}; saved {saved}'
        print('PASS topic order sync')
    except Exception as e:
        print('FAIL topic order sync:', str(e))
        raise
    finally:
        if original:
            cookies = await page.context.cookies()
            csrf = next(c['value'] for c in cookies if c['name'] == 'csrf_token')
            restored = await page.request.put(base + '/api/admin/topics/order', data={'topic_ids':original}, headers={'X-CSRF-Token':csrf})
            assert restored.status == 200