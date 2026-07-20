/**
 * 侧边栏 mini 模式下的悬浮搜索过滤按钮
 * 点击弹出输入框，输入关键词实时过滤页面上显示的链接卡片（按标题+描述匹配）
 */
(function($) {
    $(document).ready(function() {
        // 仅在 mini 侧边栏模式下显示
        if (!$('#sidebar').hasClass('mini-sidebar')) return;

        // 创建悬浮按钮
        var $btn = $('<a>', {
            href: 'javascript:',
            class: 'btn rounded-circle floating-filter-toggle',
            'data-toggle': 'tooltip',
            'data-placement': 'left',
            title: '过滤链接',
            html: '<i class="iconfont icon-search"></i>'
        });

        // 创建弹出输入框容器
        var $inputWrap = $('<div>', { class: 'floating-filter-panel', style: 'display:none' });
        var $inputGroup = $('<div>', { class: 'floating-filter-group' }).appendTo($inputWrap);
        $('<input>', {
            type: 'text',
            class: 'form-control floating-filter-input',
            placeholder: '输入关键词过滤...',
            autocomplete: 'off'
        }).appendTo($inputGroup);
        $('<span>', {
            class: 'floating-filter-count text-muted',
            style: 'display:none'
        }).appendTo($inputGroup);

        $('body').append($btn, $inputWrap);

        // 点击按钮切换输入框
        $btn.on('click', function(e) {
            e.stopPropagation();
            var visible = $inputWrap.is(':visible');
            if (visible) {
                // 已展开时再次点击：清空并关闭
                $inputWrap.find('input').val('').trigger('input');
                $inputWrap.hide();
            } else {
                $inputWrap.show();
                $inputWrap.find('input').focus();
            }
        });

        // 实时过滤
        var debounceTimer;
        $inputWrap.find('input').on('input', function() {
            clearTimeout(debounceTimer);
            var $input = $(this);
            debounceTimer = setTimeout(function() {
                doFilter($input.val());
            }, 50);
        });

        // ESC 关闭
        $(document).on('keydown', function(e) {
            if (e.key === 'Escape' && $inputWrap.is(':visible')) {
                $inputWrap.find('input').val('').trigger('input');
                $inputWrap.hide();
            }
        });

        // 点击外部关闭
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.floating-filter-panel, .floating-filter-toggle').length) {
                if ($inputWrap.is(':visible')) {
                    $inputWrap.hide();
                    $inputWrap.find('input').val('').trigger('input');
                }
            }
        });

        function doFilter(keyword) {
            keyword = $.trim(keyword).toLowerCase();

            var totalVisible = 0;

            $('.url-card').each(function() {
                var $card = $(this);
                var title = ($card.find('strong').text() || '').toLowerCase();
                var desc = ($card.find('.url-info p.text-muted').text() || '').toLowerCase();

                if (keyword === '' ||
                    title.indexOf(keyword) !== -1 ||
                    desc.indexOf(keyword) !== -1) {
                    $card.show();
                    totalVisible++;
                } else {
                    $card.hide();
                }
            });

            // 处理分组标题：同行可见数归零则隐藏
            var $headings = $('#content .d-flex.flex-fill');
            $headings.each(function() {
                var $heading = $(this);
                // 找到该标题对应的 .row
                var $nextRow = $heading.next();
                while ($nextRow.length && !$nextRow.is('.row') && !$nextRow.is('br')) {
                    $nextRow = $nextRow.next();
                }
                if ($nextRow.is('.row')) {
                    var visibleCards = $nextRow.find('.url-card:visible').length;
                    if (keyword !== '' && visibleCards === 0) {
                        $heading.hide();
                        $nextRow.hide();
                    } else {
                        $heading.show();
                        $nextRow.show();
                    }
                }
            });

            // 更新计数
            var $count = $('.floating-filter-count');
            var totalCards = $('.url-card').length;
            if (keyword !== '') {
                $count.text(totalVisible + ' / ' + totalCards).show();
            } else {
                $count.hide();
            }
        }
    });
})(jQuery);
