-- 引入 PZ-Simple UI 框架文件
require "ISUI.GlobalFunctions"
require "ISUI.ISSimpleUI"
require "ISUI.ISSimpleButton"
require "ISUI.ISSimpleImage"
require "ISUI.ISSimpleEmpty"
require "ISUI.ISSimpleText"
require "ISUI.ISSimpleTickBox"
require "ISUI.ISSimpleEntry"
require "ISUI.ISSimpleComboBox"
require "ISUI.ISSimpleScrollingListBox"
require "ISUI.ISSimpleRichText"
require "ISUI.ISSimpleProgressBar"
require "ISUI.ISSimpleImageButton"

local UI
local NoteUI
local data

-- 备注按钮点击回调
local function onNoteClick(button, args)
    -- 若备注窗口已存在，先关闭，避免重复创建
    if NoteUI then NoteUI:close(); end

    -- 备注文本在存储时已将换行符转为富文本换行标签 <BR>，直接取翻译文本即可
    local note = getText(data.note) or "";

    NoteUI = NewUI();
    NoteUI:setTitle(getText("IGUI_FlierBtnNote"));
    NoteUI:setWidthPercent(0.5);
    NoteUI:addRichText("rtext", note);
    -- 高度固定为屏幕高度的 75%
    NoteUI:setLineHeightPixel(getCore():getScreenHeight() * 0.75);
    NoteUI:saveLayout();
end

local function onCreateUI(item)
    -- 从 FlierData 中获取数据
    data = FlierData[item:getFullType()]

    -- 获取图片宽高比例（优先用数据中记录的宽高，缺失时回退到运行时纹理尺寸）
    local imgW, imgH = data.width or 0, data.height or 0
    if imgW <= 0 or imgH <= 0 then
        local tex = getTexture(data.image)
        if tex then
            imgW = tex:getWidthOrig();
            imgH = tex:getHeightOrig();
        end
    end
    local ratio = (imgW > 0 and imgH > 0) and (imgH / imgW) or 1

    -- 根据图片比例计算窗口宽度：默认 75% 屏宽，竖屏图片缩小宽度以保证高度不超出屏幕
    local screenW = getCore():getScreenWidth();
    local screenH = getCore():getScreenHeight();
    local maxH = screenH * 0.75;
    local winW = math.min(screenW * 0.75, maxH / ratio);
    winW = math.max(winW, screenW * 0.2); -- 极端竖屏时给一个最小宽度下限

    -- 创建 UI
    UI = NewUI();
    UI:setWidthPercent(winW / screenW);
    UI:setTitle(item:getDisplayName());

    -- 图片
    UI:addImage("image1", data.image);
    UI:nextLine();

    -- 下一行：左侧"正面"按钮，右侧"备注"按钮
    UI:addButton("btnNote", getText("IGUI_FlierBtnNote"), onNoteClick);

    UI:saveLayout();
end

local function onMyItemContextMenu(player, context, items)
    local items = ISInventoryPane.getActualItems(items)
    for _, item in ipairs(items) do
        if FlierData[item:getFullType()] then
            -- addOption(选项名,func的参数1,func)   注:哪个神人设计的传参
            context:addOption(
                getText('IGUI_Take_a_look'),
                item,
                onCreateUI
            )
            break
        end
    end
end

Events.OnFillInventoryObjectContextMenu.Add(onMyItemContextMenu)