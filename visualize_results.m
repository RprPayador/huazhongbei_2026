function visualize_results(filename)
    if nargin < 1
        filename = 'solution_output.txt';
    end

    % 读取文件内容
    fid = fopen(filename, 'r', 'n', 'UTF-8');
    if fid == -1
        error('无法打开文件: %s', filename);
    end
    raw = fread(fid, '*char')';
    fclose(fid);

    % 初始化数据结构
    customers = containers.Map('KeyType', 'double', 'ValueType', 'any');
    routes = {};
    
    % 解析 Section
    lines = splitlines(raw);
    section = "";
    current_route = struct();
    
    for i = 1:length(lines)
        line = strtrim(lines{i});
        if isempty(line) || startsWith(line, '#'), continue; end
        
        if strcmp(line, '[CUSTOMER]')
            section = "customer"; continue;
        elseif strcmp(line, '[META]')
            section = "meta"; continue;
        elseif startsWith(line, '[ROUTE_')
            if isfield(current_route, 'nodes')
                routes{end+1} = current_route;
            end
            current_route = struct();
            section = "route"; continue;
        elseif strcmp(line, '[UNASSIGNED]')
            section = "unassigned"; continue;
        end
        
        if section == "customer"
            parts = str2double(split(line, ','));
            if length(parts) >= 3
                customers(parts(1)) = struct('x', parts(2), 'y', parts(3));
            end
        elseif section == "route"
            if contains(line, '=')
                kv = split(line, '=');
                key = strtrim(kv{1}); val = strtrim(kv{2});
                if strcmp(key, 'nodes')
                    current_route.nodes = str2double(split(val, ','))';
                elseif strcmp(key, 'times')
                    current_route.times = str2double(split(val, ','))';
                elseif strcmp(key, 'vehicle_id')
                    current_route.vid = str2double(val);
                elseif strcmp(key, 'vehicle_type')
                    current_route.type = str2double(val);
                end
            end
        end
    end
    if isfield(current_route, 'nodes'), routes{end+1} = current_route; end

    %% --- 绘图 1: 车辆路径图 ---
    figure('Name', '车辆路径可视化', 'Color', 'w', 'Position', [100, 100, 800, 700]);
    hold on; box on; grid on;
    
    % 画客户点
    c_keys = cell2mat(customers.keys);
    xs = []; ys = [];
    for k = c_keys
        c = customers(k);
        if k == 0
            plot(c.x, c.y, 'rp', 'MarkerSize', 15, 'MarkerFaceColor', 'r', 'DisplayName', '配送中心');
        else
            plot(c.x, c.y, 'o', 'Color', [0.7 0.7 0.7], 'MarkerSize', 4);
            text(c.x+0.5, c.y+0.5, num2str(k), 'FontSize', 7, 'Color', [0.5 0.5 0.5]);
        end
        xs(end+1) = c.x; ys(end+1) = c.y;
    end
    
    % 画路径
    colors = lines(min(length(routes), 256));
    for r = 1:length(routes)
        nodes = routes{r}.nodes + 1; % MATLAB 1-indexed
        node_ids = routes{r}.nodes;
        route_x = []; route_y = [];
        for n = node_ids
            c = customers(n);
            route_x(end+1) = c.x;
            route_y(end+1) = c.y;
        end
        plot(route_x, route_y, '-', 'LineWidth', 1.2, 'Color', colors(mod(r,256)+1,:));
        % 画个箭头方向
        if length(route_x) > 2
            mid = floor(length(route_x)/2);
            quiver(route_x(mid), route_y(mid), route_x(mid+1)-route_x(mid), route_y(mid+1)-route_y(mid), ...
                0.5, 'MaxHeadSize', 2, 'Color', colors(mod(r,256)+1,:));
        end
    end
    
    xlabel('X 坐标 (km)'); ylabel('Y 坐标 (km)');
    title(['车辆路径图 (总路径数: ', num2str(length(routes)), ')']);
    axis equal;

    %% --- 绘图 2: 排班甘特图 ---
    figure('Name', '车辆排班甘特图', 'Color', 'w', 'Position', [950, 100, 900, 700]);
    hold on; box on;
    
    % 提取车辆任务
    vids = [];
    for r = 1:length(routes)
        vids(end+1) = routes{r}.vid;
    end
    unique_vids = unique(vids);
    y_map = containers.Map(unique_vids, 1:length(unique_vids));
    
    for r = 1:length(routes)
        rt = routes{r};
        y = y_map(rt.vid);
        t_start = rt.times(1);
        t_end = rt.times(end);
        
        % 颜色区分：4,5是新能源(蓝)，1,2,3是燃油(橙)
        if rt.type >= 4
            col = [0.2 0.6 1.0]; % 蓝色
        else
            col = [1.0 0.6 0.2]; % 橙色
        end
        
        rectangle('Position', [t_start, y-0.3, t_end-t_start, 0.6], ...
            'FaceColor', col, 'EdgeColor', 'w', 'Curvature', 0.2);
        
        if (t_end - t_start) > 40
            text(t_start + (t_end-t_start)/2, y, sprintf('%02d:%02d', floor(t_start/60), mod(floor(t_start),60)), ...
                'HorizontalAlignment', 'center', 'FontSize', 7, 'Color', 'w', 'FontWeight', 'bold');
        end
    end
    
    % 设置轴
    set(gca, 'YTick', 1:length(unique_vids), 'YTickLabel', string(unique_vids));
    set(gca, 'YDir', 'reverse');
    
    % 时间轴标签 (08:00 - 24:00)
    xticks = 480:120:1440;
    xticklabels = {};
    for t = xticks
        xticklabels{end+1} = sprintf('%02d:00', floor(t/60));
    end
    set(gca, 'XTick', xticks, 'XTickLabel', xticklabels);
    xlabel('配送时间'); ylabel('车辆 ID');
    title('车辆排班计划 (蓝色: 新能源, 橙色: 燃油)');
    grid on;
    xlim([450, 1450]);
    
    % 画高峰时段阴影
    y_lim = get(gca, 'YLim');
    patch([480 540 540 480], [y_lim(1) y_lim(1) y_lim(2) y_lim(2)], [1 0 0], 'FaceAlpha', 0.05, 'EdgeColor', 'none', 'HandleVisibility', 'off');
    patch([1020 1140 1140 1020], [y_lim(1) y_lim(1) y_lim(2) y_lim(2)], [1 0 0], 'FaceAlpha', 0.05, 'EdgeColor', 'none', 'HandleVisibility', 'off');
end
