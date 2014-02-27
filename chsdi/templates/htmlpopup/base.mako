# -*- coding: utf-8 -*-

<% 
  c = pageargs['feature']
  protocol = request.scheme
  c['bbox'] = pageargs.get('bbox')
  c['scale'] = pageargs.get('scale')
  c['stable_id'] = False
  extended = pageargs.get('extended')
  extendedPathCss = request.static_url('chsdi:static/css/extended.min.css')
  c['baseUrl'] = protocol + '://' + request.registry.settings['geoadminhost']
  c['instanceId'] = request.registry.settings['instanceid']
  bbox = c['bbox']
  lang = request.lang
  attribution = pageargs.get('attribution')
  fullName = pageargs.get('fullName')
  topic = request.matchdict.get('map')
%>

% if extended:
  <meta name="viewport" content="initial-scale=1.0"/>
  <link rel="stylesheet" type="text/css" href="${h.versioned(extendedPathCss)}"/>
  <link rel="stylesheet" type="text/css" href="../../../../../../static/css/blueimp-gallery-2.11.0.min.css"/>
  <script src="../../../../../../static/js/jquery-2.0.3.min.js"></script>
  <script src="../../../../../../static/js/blueimp-gallery-2.11.5.min.js"></script>
  <link rel="shortcut icon" type="image/x-icon" href="${h.versioned(request.static_url('chsdi:static/images/favicon.ico'))}">
% endif

% if extended:
<div class="chsdi-htmlpopup-container">
% else:
<div class="htmlpopup-container">
% endif
  <div class="htmlpopup-header">
    <span>${fullName}</span> (${attribution})
  </div>
  <div class="htmlpopup-content">
    % if extended:
      ${self.extended_info(c, lang)}
    % else:
      <span>${_('Information')}</span>
      <br>
      <table>
        ${self.table_body(c, lang)}
        % if c['stable_id'] is True:
          <tr>
            <td class="cell-left"></td>
            <td>
              <a href="${c['baseUrl']}?${c['layerBodId']}=${c['featureId']}&lang=${lang}&topic=${topic}" target="new">
                ${_('Link to object')}
              </a>
            </td>
          </tr>
        %endif
      </table>
    % endif
  </div>
  % if extended:
  <div class="htmlpopup-footer">
    <a href="${_('disclaimer url')}" target="_blank">
      ${_('disclaimer title')}
    </a>
    <div class="float-right">
      % if c['stable_id'] is True:
      <a class="link-red" href="${c['baseUrl']}?${c['layerBodId']}=${c['featureId']}&lang=${lang}&topic=${topic}" target="new">
        ${_('Link to object')}
      </a>
      &nbsp;|&nbsp;
      % endif
      <a href="javascript:window.print();">
        ${_('print')}
      </a>
    </div>
    </div>
  </div>
  % endif
</div>
