/**
 * 页面内链接卡片实时过滤
 * 通过侧边栏搜索图标弹窗 #search-modal 输入关键词过滤 .url-card
 */
(function($) {

    // 实时过滤核心函数
    function doFilter(keyword) {
        keyword = $.trim(keyword).toLowerCase();

        var totalVisible = 0;
        var totalCards = $('.url-card').length;

        $('.url-card').each(function() {
            var $card = $(this);
            // 标题：strong 标签内的文字
            var title = ($card.find('strong').text() || '').toLowerCase();
            // 描述：p.text-muted 的文字
            var desc = ($card.find('p.text-muted').text() || '').toLowerCase();

            if (keyword === '' ||
                title.indexOf(keyword) !== -1 ||
                desc.indexOf(keyword) !== -1) {
                $card.show();
                totalVisible++;
            } else {
                $card.hide();
            }
        });

        // 隐藏空分类标题
        var $headings = $('#content .d-flex.flex-fill:not(.flex-tab)');
        $headings.each(function() {
            var $heading = $(this);
            var $nextRow = $heading.next();
            while ($nextRow.length && !$nextRow.is('.row') && $nextRow.attr('class') !== 'row') {
                $nextRow = $nextRow.next();
            }
            if ($nextRow.is('.row')) {
                var visibleCards = $nextRow.find('.url-card:visible').length;
                if (keyword !== '' && visibleCards === 0) {
                    $heading.hide();
                } else {
                    $heading.show();
                }
            }
        });

        // 更新计数
        var $count = $('#modal-filter-count');
        if (keyword !== '') {
            $count.text(totalVisible + ' / ' + totalCards).show();
        } else {
            $count.hide();
        }
    }

    $(document).ready(function() {
        var $modal = $('#search-modal');
        var $input = $('#modal-filter-input');

        // 弹窗显示时：隐藏 Bootstrap 遮罩层 + 清空输入 + 聚焦
        $modal.on('shown.bs.modal', function() {
            $('.modal-backdrop').hide();
            $input.val('').focus();
            doFilter('');
        });

        // 弹窗关闭时：恢复遮罩层 + 恢复全部卡片显示
        $modal.on('hidden.bs.modal', function() {
            $('.modal-backdrop').show();
            doFilter('');
        });

        // 实时过滤（50ms 防抖）
        var debounceTimer;
        $input.on('input', function() {
            clearTimeout(debounceTimer);
            var val = $(this).val();
            debounceTimer = setTimeout(function() {
                doFilter(val);
            }, 50);
        });
    });

})(jQuery);
