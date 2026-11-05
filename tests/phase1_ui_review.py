# Reusable browser checks corresponding to flows exercised through browser automation during iteration 2.
# Browser-tool harness should call: await run_review(page, base_url, credentials).
async def run_review(page, base_url, credentials):
    await page.set_viewport_size({'width': 1920, 'height': 1080})

    async def login(role, target):
        await page.context.clear_cookies()
        await page.goto(base_url + '/auth?mode=login')
        await page.get_by_test_id('login-email-input').fill(credentials[role]['email'])
        await page.get_by_test_id('login-password-input').fill(credentials[role]['password'])
        await page.get_by_test_id('login-submit-button').click(force=True)
        await page.wait_for_url('**/' + target, timeout=20000)

    try:
        await login('Admin', 'admin')
        await page.get_by_test_id('admin-dashboard-tabs').wait_for(timeout=20000)
        for tab, panel in [('overview', 'admin-metric-teams'), ('people', 'admin-participants-table'),
                           ('topics', 'admin-topics-panel'), ('applications', 'admin-applications-panel'),
                           ('payments', 'admin-payments-panel'), ('timeline', 'admin-timeline-form'),
                           ('projects', 'admin-projects-panel'), ('judging', 'admin-judging-panel'),
                           ('security', 'admin-security-panel')]:
            await page.get_by_test_id('admin-tab-' + tab).click(force=True)
            await page.get_by_test_id(panel).wait_for(timeout=15000)
            print('PASS admin tab', tab)
        await page.get_by_test_id('admin-tab-applications').click(force=True)
        await page.get_by_test_id('manual-application-date-input').fill('2026-11-01T12:30')
        await page.wait_for_timeout(300)
        assert await page.get_by_test_id('manual-application-date-input').input_value(), 'Manual application date cleared'
        print('PASS manual datetime entry')
    except Exception as error:
        print('FAIL admin review:', str(error))

    try:
        await login('Phase 1 Team Leader', 'dashboard')
        await page.get_by_test_id('team-overview-panel').wait_for(timeout=20000)
        for tab, panel in [('abstract', 'abstract-panel'), ('payment', 'payment-panel'),
                           ('project', 'project-panel'), ('notifications', 'notifications-panel')]:
            await page.get_by_test_id('participant-tab-' + tab).click(force=True)
            await page.get_by_test_id(panel).wait_for(timeout=15000)
            print('PASS participant tab', tab)
        await page.get_by_test_id('participant-tab-abstract').click(force=True)
        async with page.expect_download(timeout=30000) as download:
            await page.get_by_test_id('abstract-private-download').click(force=True)
        assert (await download.value).suggested_filename.endswith('.pdf')
        print('PASS private file download')
        assert await page.evaluate('localStorage.getItem("sk_token")') is None
        await page.context.clear_cookies(name='access_token')
        await page.reload()
        await page.wait_for_timeout(1800)
        assert '/auth' not in page.url, 'Valid refresh cookie did not restore session on reload'
        print('PASS session recovery')
    except Exception as error:
        print('FAIL participant review:', str(error))

    try:
        await login('Judge', 'judge')
        await page.get_by_test_id('judge-dashboard').wait_for(timeout=20000)
        await page.set_viewport_size({'width': 390, 'height': 844})
        assert not await page.evaluate('document.documentElement.scrollWidth > innerWidth')
        print('PASS mobile judge layout')
    except Exception as error:
        print('FAIL judge review:', str(error))

    error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(', ');
    }""")
    print(f'Found error message: {error_text}' if error_text else 'No error messages found on the page')