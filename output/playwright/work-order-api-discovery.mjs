const apiBase = 'https://main-api.hubbuyer.com';
const account = process.env.WO_TEST_ACCOUNT || '';
const password = process.env.WO_TEST_PASSWORD || '';
const label = process.env.WO_TEST_LABEL || 'account';

if (!account || !password) throw new Error('Missing test credentials');

const post = async (path, data, token = '') => {
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: token,
      LoginType: 'admin',
      version: '0.0.0',
    },
    body: JSON.stringify(data),
  });
  const body = await response.json().catch(() => ({}));
  return { httpStatus: response.status, body };
};

const login = await post('/admin/login/login', { account, password });
if (login.body?.code !== 200 || !login.body?.data?.login_token) {
  console.log(JSON.stringify({
    label,
    login: { httpStatus: login.httpStatus, code: login.body?.code, msg: login.body?.msg },
  }, null, 2));
  process.exit(1);
}

const token = login.body.data.login_token;
const orderResult = await post('/admin_b2b/order/list', {
  user_info: 'JPN62',
  status: 0,
  page: 1,
  limit: 50,
}, token);
const todoResult = await post('/admin_b2b/workOrder/todoList', {
  mode: 'all',
  tab_type: 'all',
  page: 1,
  pageSize: 200,
  limit: 200,
}, token);

const orderRows = orderResult.body?.data?.order_data || orderResult.body?.data?.list || [];
const orders = orderRows.slice(0, 30).map((row) => ({
  id: row.id,
  uuid: row.uuid,
  order_no: row.order_no,
  user_uuid: row.user_uuid,
  user_main_uuid: row.user_main_uuid,
  status: row.status,
  sale_admin_id: row.sale_admin_id,
  purchase_admin_id: row.purchase_admin_id,
  csp_manager_admin_id: row.csp_manager_admin_id,
}));

const orderDetails = [];
for (const order of orders.slice(0, 10)) {
  const detailResult = await post('/admin_b2b/orderDetail/list', { order_no: order.order_no }, token);
  const data = detailResult.body?.data || {};
  const sellerRows = Array.isArray(data.order_seller_data) ? data.order_seller_data : [];
  const rows = sellerRows.flatMap((seller) => Array.isArray(seller.detail_data) ? seller.detail_data : []);
  orderDetails.push({
    order_no: order.order_no,
    code: detailResult.body?.code,
    msg: detailResult.body?.msg,
    rows: Array.isArray(rows) ? rows.slice(0, 20).map((row) => ({
      id: row.id,
      uuid: row.uuid,
      item_id: row.item_id,
      sku_text: row.sku_text || row.sku || row.specification || '',
      status: row.status,
      purchase_status: row.purchase_status,
      work_order_count: row.work_order_count,
      unfinished_work_order_count: row.unfinished_work_order_count,
      latest_work_order_id: row.latest_work_order_id,
      latest_work_order_no: row.latest_work_order_no,
    })) : [],
  });
}

const todoData = todoResult.body?.data || {};
const todoRows = todoData.list || todoData.data || [];
const todos = Array.isArray(todoRows) ? todoRows.slice(0, 200).map((row) => ({
  id: row.id,
  uuid: row.uuid,
  work_order_no: row.work_order_no,
  order_no: row.order_no,
  order_detail_id: row.order_detail_id,
  user_uuid: row.user_uuid,
  user_main_uuid: row.user_main_uuid,
  status: row.status,
  current_admin_id: row.current_admin_id,
  initiator_admin_id: row.initiator_admin_id,
  latest_record_type: row.latest_record_type,
})) : [];

const admin = login.body?.data?.admin || {};
console.log(JSON.stringify({
  label,
  login: {
    httpStatus: login.httpStatus,
    code: login.body?.code,
    admin_id: admin.id || admin.login_id,
    role_ids: admin.role_ids || admin.group_ids || [],
  },
  orderQuery: {
    httpStatus: orderResult.httpStatus,
    code: orderResult.body?.code,
    msg: orderResult.body?.msg,
    total: orderResult.body?.data?.order_total ?? orderResult.body?.data?.total,
    orders,
  },
  orderDetails,
  todoQuery: {
    httpStatus: todoResult.httpStatus,
    code: todoResult.body?.code,
    msg: todoResult.body?.msg,
    total: todoData.total,
    todos,
  },
}, null, 2));
