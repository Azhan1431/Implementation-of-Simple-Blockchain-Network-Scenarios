// 区块链金融系统前端交互逻辑
document.addEventListener('DOMContentLoaded', function() {
    // 创建账户
    document.getElementById('createAccount').addEventListener('click', function() {
        axios.get('/account_create')
            .then(response => {
                const account = response.data.data;
                document.getElementById('accountDetails').textContent = 
                    `地址: ${account.address}\n私钥: ${account.private_key}\n公钥: ${account.public_key}`;
                document.getElementById('accountInfo').style.display = 'block';
                
                // 自动填充转账表单的发送方地址和私钥
                document.getElementById('sender').value = account.address;
                document.getElementById('privateKey').value = account.private_key;
            })
            .catch(error => {
                alert('创建账户失败: ' + error.message);
            });
    });

    // 提交转账交易
    document.getElementById('transferForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const transaction = {
            sender: document.getElementById('sender').value,
            recipient: document.getElementById('recipient').value,
            data: document.getElementById('amount').value,
            private_key: document.getElementById('privateKey').value
        };

        axios.post('/add_transaction', transaction)
            .then(response => {
                const resultDiv = document.getElementById('transferResult');
                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        交易提交成功！交易ID: ${response.data.tx_id}
                    </div>
                `;
                document.getElementById('transferForm').reset();
            })
            .catch(error => {
                const resultDiv = document.getElementById('transferResult');
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        交易失败: ${error.response?.data?.message || error.message}
                    </div>
                `;
            });
    });

    // 查询区块
    document.getElementById('queryBlock').addEventListener('click', function() {
        const blockHeight = document.getElementById('blockHeight').value;
        if (!blockHeight) {
            alert('请输入区块高度');
            return;
        }

        axios.get(`/block_query?id=${blockHeight}`)
            .then(response => {
                const resultDiv = document.getElementById('blockResult');
                resultDiv.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h6>区块 ${blockHeight} 内容</h6>
                            <pre>${JSON.stringify(response.data, null, 2)}</pre>
                        </div>
                    </div>
                `;
            })
            .catch(error => {
                const resultDiv = document.getElementById('blockResult');
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        查询失败: ${error.response?.data || error.message}
                    </div>
                `;
            });
    });

    // 查询交易池
    document.getElementById('queryPool').addEventListener('click', function() {
        axios.get('/get_pool')
            .then(response => {
                const resultDiv = document.getElementById('poolResult');
                resultDiv.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h6>当前交易池</h6>
                            <pre>${JSON.stringify(response.data.data, null, 2)}</pre>
                        </div>
                    </div>
                `;
            })
            .catch(error => {
                const resultDiv = document.getElementById('poolResult');
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        查询失败: ${error.message}
                    </div>
                `;
            });
    });
});
