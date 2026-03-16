import React, { useState, useEffect } from 'react';
import {
  Card, Button, Table, Modal, Form, Input, Select, Upload, message,
  Popconfirm, Tag, Space, Drawer, Progress, Empty, Typography,
  Collapse, Switch, InputNumber, Tooltip, Divider, Alert
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, FileTextOutlined,
  BookOutlined, EditOutlined, InboxOutlined, ReloadOutlined,
  SettingOutlined, QuestionCircleOutlined, ApartmentOutlined
} from '@ant-design/icons';
import type { RcFile } from 'antd/es/upload/interface';
import { knowledgeApi } from '../services/knowledgeApi';
import type { KnowledgeBase, KBDocument, ProcessingStage } from '../types/knowledge';
import { EMBEDDING_MODELS, DEFAULT_RAG_CONFIG, PROCESSING_STAGE_INFO, LLM_MODELS } from '../types/knowledge';
import KnowledgeGraph from '../components/Knowledge/KnowledgeGraph';

const { Dragger } = Upload;
const { Text } = Typography;
const { Panel } = Collapse;

// 支持的文件类型
const ACCEPTED_FILE_TYPES = '.pdf,.doc,.docx,.txt,.md';

// 切片策略选项
const CHUNKING_STRATEGIES = [
  { value: 'fixed', label: '固定切片', desc: '按固定字符数切分，简单高效' },
  { value: 'semantic', label: '语义切片 (P3)', desc: '基于语义相似度智能切分，保持语义完整性' },
  { value: 'parent_child', label: '父子文档 (P4)', desc: '大chunk存储，小chunk检索，兼顾精度和上下文' },
];

// 检索策略选项
const RETRIEVAL_STRATEGIES = [
  { value: 'basic', label: '基础检索', desc: '仅向量检索' },
  { value: 'hybrid', label: '混合检索', desc: '向量 + BM25 + RRF融合 + Rerank' },
  { value: 'contextual', label: '上下文检索 (P1)', desc: '为chunk添加文档上下文，提升召回准确性' },
  { value: 'hyde', label: 'HyDE (P2)', desc: '生成假设文档进行检索，弥合query-doc语义鸿沟' },
  { value: 'multi_query', label: '多查询改写 (P2)', desc: '将query改写为多个变体，提高召回覆盖率' },
  { value: 'graph_rag', label: 'GraphRAG (P5)', desc: '知识图谱增强，适合跨文档推理' },
];

// 策略搭配建议数据
const STRATEGY_RECOMMENDATIONS = [
  { key: '1', chunking: '固定切片', retrieval: '混合检索', scenario: '通用场景', advantage: '简单稳定，适合大多数文档', rating: '⭐⭐⭐⭐⭐' },
  { key: '2', chunking: '语义切片', retrieval: 'HyDE', scenario: '高精度问答', advantage: '语义完整 + 假设文档，精准匹配', rating: '⭐⭐⭐⭐⭐' },
  { key: '3', chunking: '父子文档', retrieval: '混合检索', scenario: '长文档/技术文档', advantage: '小块检索大块返回，上下文丰富', rating: '⭐⭐⭐⭐' },
  { key: '4', chunking: '语义切片', retrieval: '多查询改写', scenario: '复杂问题', advantage: '多角度检索，召回覆盖率高', rating: '⭐⭐⭐⭐' },
  { key: '5', chunking: '固定切片', retrieval: 'GraphRAG', scenario: '知识密集型', advantage: '实体关系抽取，支持多跳推理', rating: '⭐⭐⭐⭐' },
  { key: '6', chunking: '固定切片', retrieval: '上下文检索', scenario: '短文档集合', advantage: '添加文档上下文，提升相关性', rating: '⭐⭐⭐' },
];

// 策略搭配建议表格列
const recommendationColumns = [
  { title: '切片方式', dataIndex: 'chunking', key: 'chunking', width: 100 },
  { title: '检索方式', dataIndex: 'retrieval', key: 'retrieval', width: 120 },
  { title: '适用场景', dataIndex: 'scenario', key: 'scenario', width: 120 },
  { title: '优势', dataIndex: 'advantage', key: 'advantage' },
  { title: '推荐度', dataIndex: 'rating', key: 'rating', width: 100 },
];

interface UploadingFile {
  uid: string;
  name: string;
  status: 'uploading' | 'done' | 'error';
  progress: number;
  errorMsg?: string;
}

const KnowledgeBasePage: React.FC = () => {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingKB, setEditingKB] = useState<KnowledgeBase | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [graphDrawerOpen, setGraphDrawerOpen] = useState(false);
  const [graphKB, setGraphKB] = useState<KnowledgeBase | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadKBs();
  }, []);

  // 处理中状态轮询
  useEffect(() => {
    if (!selectedKB || !detailDrawerOpen) return;

    const processingDocs = documents.filter(doc => doc.status === 'processing');
    if (processingDocs.length === 0) return;

    const interval = setInterval(async () => {
      try {
        // 对每个处理中的文档调用 check-status 接口
        for (const doc of processingDocs) {
          await knowledgeApi.checkDocumentStatus(selectedKB.id, doc.id);
        }
        // 刷新文档列表
        const docs = await knowledgeApi.listDocuments(selectedKB.id);
        setDocuments(docs);
        // 如果没有处理中的文档了，刷新知识库列表
        if (!docs.some(d => d.status === 'processing')) {
          loadKBs();
        }
      } catch (e) {
        console.error('轮询文档状态失败', e);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [selectedKB, detailDrawerOpen, documents]);

  const loadKBs = async () => {
    setLoading(true);
    try {
      const data = await knowledgeApi.listKBs();
      setKBs(data);
    } catch (e) {
      message.error('加载知识库失败');
    } finally {
      setLoading(false);
    }
  };

  // 打开创建 Modal
  const openCreateModal = () => {
    setEditingKB(null);
    form.resetFields();
    form.setFieldsValue({
      embedding_model: 'text-embedding-v4',
      rag_config: DEFAULT_RAG_CONFIG
    });
    setModalOpen(true);
  };

  // 打开编辑 Modal
  const openEditModal = (kb: KnowledgeBase) => {
    setEditingKB(kb);
    form.setFieldsValue({
      name: kb.name,
      description: kb.description,
      embedding_model: kb.embedding_model,
      rag_config: kb.rag_config || DEFAULT_RAG_CONFIG,
    });
    setModalOpen(true);
  };

  // 创建或更新知识库
  const handleSubmit = async (values: any) => {
    try {
      if (editingKB) {
        await knowledgeApi.updateKB(editingKB.id, {
          name: values.name,
          description: values.description,
          rag_config: values.rag_config,
        });
        message.success('更新成功');
      } else {
        await knowledgeApi.createKB({
          name: values.name,
          description: values.description,
          embedding_model: values.embedding_model,
          rag_config: values.rag_config,
        });
        message.success('创建成功');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingKB(null);
      loadKBs();
    } catch (e) {
      message.error(editingKB ? '更新失败' : '创建失败');
    }
  };
  const handleDelete = async (kbId: string) => {
    try {
      await knowledgeApi.deleteKB(kbId);
      message.success('删除成功');
      loadKBs();
    } catch (e) {
      message.error('删除失败');
    }
  };

  // 打开图谱 Drawer
  const openGraphDrawer = (kb: KnowledgeBase) => {
    console.log(`[KnowledgeBasePage] 打开图谱 | kb_id=${kb.id} | name=${kb.name}`);
    setGraphKB(kb);
    setGraphDrawerOpen(true);
  };

  const openDetail = async (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setDetailDrawerOpen(true);
    setUploadingFiles([]);
    try {
      const docs = await knowledgeApi.listDocuments(kb.id);
      setDocuments(docs);
    } catch (e) {
      message.error('加载文档失败');
    }
  };

  // 批量上传处理
  const handleBatchUpload = async (files: RcFile[]) => {
    if (!selectedKB) return;

    // 初始化上传队列
    const initialFiles: UploadingFile[] = files.map(f => ({
      uid: f.uid,
      name: f.name,
      status: 'uploading',
      progress: 0,
    }));
    setUploadingFiles(prev => [...prev, ...initialFiles]);

    // 逐个上传
    for (const file of files) {
      try {
        // 模拟进度更新
        setUploadingFiles(prev =>
          prev.map(f => f.uid === file.uid ? { ...f, progress: 30 } : f)
        );

        await knowledgeApi.uploadDocument(selectedKB.id, file);

        setUploadingFiles(prev =>
          prev.map(f => f.uid === file.uid ? { ...f, status: 'done', progress: 100 } : f)
        );
      } catch (e) {
        setUploadingFiles(prev =>
          prev.map(f => f.uid === file.uid ? { ...f, status: 'error', errorMsg: '上传失败' } : f)
        );
      }
    }

    // 刷新文档列表
    const docs = await knowledgeApi.listDocuments(selectedKB.id);
    setDocuments(docs);
    loadKBs();

    // 3秒后清除已完成的上传项
    setTimeout(() => {
      setUploadingFiles(prev => prev.filter(f => f.status === 'uploading'));
    }, 3000);
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!selectedKB) return;
    try {
      await knowledgeApi.deleteDocument(selectedKB.id, docId);
      message.success('删除成功');
      const docs = await knowledgeApi.listDocuments(selectedKB.id);
      setDocuments(docs);
      loadKBs();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: KnowledgeBase) => (
        <a onClick={() => openDetail(record)}><BookOutlined /> {text}</a>
      )
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: 'Embedding 模型', dataIndex: 'embedding_model', key: 'embedding_model' },
    {
      title: 'RAG策略',
      key: 'rag_strategy',
      render: (_: any, record: KnowledgeBase) => {
        const config = record.rag_config;
        if (!config) return <Tag>默认</Tag>;
        const chunkLabel = CHUNKING_STRATEGIES.find(s => s.value === config.chunking_strategy)?.label || config.chunking_strategy;
        const retrievalLabel = RETRIEVAL_STRATEGIES.find(s => s.value === config.retrieval_strategy)?.label || config.retrieval_strategy;
        return (
          <Space direction="vertical" size={0}>
            <Tag color="blue">{chunkLabel}</Tag>
            <Tag color="green">{retrievalLabel}</Tag>
          </Space>
        );
      }
    },
    { title: '文档数', dataIndex: 'doc_count', key: 'doc_count' },
    { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => new Date(t).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: KnowledgeBase) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            编辑
          </Button>
          {record.rag_config?.retrieval_strategy === 'graph_rag' && (
            <Button
              type="link"
              icon={<ApartmentOutlined />}
              onClick={() => openGraphDrawer(record)}
            >
              图谱
            </Button>
          )}
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ];

  const docColumns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (t: string) => <><FileTextOutlined /> {t}</>
    },
    { title: '类型', dataIndex: 'file_type', key: 'file_type' },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (s: number) => `${(s / 1024).toFixed(1)} KB`
    },
    { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 220,
      render: (_: string, record: KBDocument) => {
        if (record.status === 'processing') {
          const stageInfo = PROCESSING_STAGE_INFO[record.processing_stage as ProcessingStage] || PROCESSING_STAGE_INFO[''];
          return (
            <Space direction="vertical" size={0} style={{ width: '100%' }}>
              <Space>
                <Tag color={stageInfo.color}>{stageInfo.label}</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {record.processing_message || '处理中...'}
                </Text>
              </Space>
              <Progress
                percent={record.processing_progress || 0}
                size="small"
                status="active"
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </Space>
          );
        }

        if (record.status === 'completed') {
          const detailMessage =
            record.processing_message && record.processing_message !== '处理完成'
              ? record.processing_message
              : record.error_msg;
          return (
            <Space direction="vertical" size={0} style={{ width: '100%' }}>
              <Tag color="green">已完成</Tag>
              {detailMessage && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {detailMessage}
                </Text>
              )}
            </Space>
          );
        }

        if (record.status === 'failed') {
          return (
            <Tooltip title={record.error_msg}>
              <Tag color="red">失败</Tag>
            </Tooltip>
          );
        }

        return <Tag>待处理</Tag>;
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: KBDocument) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDeleteDoc(record.id)}>
          <Button type="link" danger size="small">删除</Button>
        </Popconfirm>
      )
    },
  ];

  // 知识库列表空状态
  const renderKBEmpty = () => (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description="暂无知识库"
    >
      <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
        创建第一个知识库
      </Button>
    </Empty>
  );

  // 文档列表空状态
  const renderDocEmpty = () => (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description="暂无文档，拖拽文件到此处或点击上传"
    />
  );

  // 上传队列渲染
  const renderUploadQueue = () => {
    if (uploadingFiles.length === 0) return null;

    return (
      <Card size="small" title="上传队列" style={{ marginBottom: 16 }}>
        {uploadingFiles.map(file => (
          <div key={file.uid} style={{ marginBottom: 8 }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Text ellipsis style={{ maxWidth: 300 }}>
                <FileTextOutlined /> {file.name}
              </Text>
              <Tag color={file.status === 'done' ? 'green' : file.status === 'error' ? 'red' : 'blue'}>
                {file.status === 'done' ? '完成' : file.status === 'error' ? '失败' : '上传中'}
              </Tag>
            </Space>
            <Progress
              percent={file.progress}
              size="small"
              status={file.status === 'error' ? 'exception' : file.status === 'done' ? 'success' : 'active'}
            />
          </div>
        ))}
      </Card>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="知识库管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            新建知识库
          </Button>
        }
      >
        {kbs.length === 0 && !loading ? (
          renderKBEmpty()
        ) : (
          <Table columns={columns} dataSource={kbs} rowKey="id" loading={loading} />
        )}
      </Card>

      <Modal
        title={editingKB ? '编辑知识库' : '新建知识库'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditingKB(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="知识库名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="知识库描述" rows={2} />
          </Form.Item>
          <Form.Item name="embedding_model" label="Embedding 模型" initialValue="text-embedding-v4">
            <Select
              showSearch
              optionFilterProp="label"
              options={EMBEDDING_MODELS.map(m => ({
                label: `${m.name} (${m.dimension}维)`,
                value: m.model_id
              }))}
              disabled={!!editingKB}
              placeholder="选择 Embedding 模型"
            />
          </Form.Item>
          {editingKB && (
            <Text type="secondary">注：Embedding 模型创建后不可修改</Text>
          )}

          <Divider>
            <Space>
              <SettingOutlined />
              RAG 优化配置
            </Space>
          </Divider>

          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="策略搭配建议"
            description={
              <Table
                dataSource={STRATEGY_RECOMMENDATIONS}
                columns={recommendationColumns}
                size="small"
                pagination={false}
                style={{ marginTop: 8 }}
              />
            }
          />

          <Collapse ghost defaultActiveKey={['chunking', 'retrieval']}>
            <Panel header="切片策略" key="chunking">
              <Form.Item
                name={['rag_config', 'chunking_strategy']}
                label={
                  <Space>
                    切片方式
                    <Tooltip title="决定如何将文档切分为小块">
                      <QuestionCircleOutlined />
                    </Tooltip>
                  </Space>
                }
              >
                <Select
                  options={CHUNKING_STRATEGIES.map(s => ({
                    label: <span>{s.label} <Text type="secondary">- {s.desc}</Text></span>,
                    value: s.value
                  }))}
                />
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prev, cur) =>
                prev?.rag_config?.chunking_strategy !== cur?.rag_config?.chunking_strategy
              }>
                {({ getFieldValue }) => {
                  const strategy = getFieldValue(['rag_config', 'chunking_strategy']);
                  return (
                    <>
                      {strategy === 'fixed' && (
                        <Space>
                          <Form.Item name={['rag_config', 'chunk_size']} label="切片大小">
                            <InputNumber min={100} max={2000} addonAfter="字符" />
                          </Form.Item>
                          <Form.Item name={['rag_config', 'chunk_overlap']} label="重叠大小">
                            <InputNumber min={0} max={500} addonAfter="字符" />
                          </Form.Item>
                        </Space>
                      )}
                      {strategy === 'semantic' && (
                        <>
                          <Alert
                            type="info"
                            showIcon
                            message="语义切片说明"
                            description="语义切片根据句子间的语义相似度自动决定切分位置，不使用固定大小和重叠参数。切片大小由语义阈值控制。"
                            style={{ marginBottom: 16 }}
                          />
                          <Form.Item
                            name={['rag_config', 'semantic_threshold']}
                            label={
                              <Space>
                                语义阈值
                                <Tooltip title="相邻句子相似度低于此值时切分。阈值越高切片越小越多，阈值越低切片越大越少。推荐：0.5-0.6">
                                  <QuestionCircleOutlined />
                                </Tooltip>
                              </Space>
                            }
                          >
                            <InputNumber min={0.1} max={0.9} step={0.1} />
                          </Form.Item>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            • 0.3-0.4：宽松切分（大块，适合长文档）<br />
                            • 0.5-0.6：平衡切分（推荐，适合大多数场景）<br />
                            • 0.7-0.8：严格切分（小块，适合精细问答）
                          </Text>
                        </>
                      )}
                      {strategy === 'parent_child' && (
                        <Space>
                          <Form.Item name={['rag_config', 'parent_chunk_size']} label="父文档大小">
                            <InputNumber min={500} max={5000} addonAfter="字符" />
                          </Form.Item>
                          <Form.Item name={['rag_config', 'child_chunk_size']} label="子文档大小">
                            <InputNumber min={50} max={500} addonAfter="字符" />
                          </Form.Item>
                        </Space>
                      )}
                    </>
                  );
                }}
              </Form.Item>
            </Panel>

            <Panel header="检索策略" key="retrieval">
              <Form.Item
                name={['rag_config', 'retrieval_strategy']}
                label={
                  <Space>
                    检索方式
                    <Tooltip title="决定如何从知识库中检索相关内容">
                      <QuestionCircleOutlined />
                    </Tooltip>
                  </Space>
                }
              >
                <Select
                  options={RETRIEVAL_STRATEGIES.map(s => ({
                    label: <span>{s.label} <Text type="secondary">- {s.desc}</Text></span>,
                    value: s.value
                  }))}
                />
              </Form.Item>

              <Form.Item
                name={['rag_config', 'use_chinese_tokenizer']}
                label={
                  <Space>
                    中文分词优化 (P0)
                    <Tooltip title="使用jieba分词提升BM25对中文的检索效果">
                      <QuestionCircleOutlined />
                    </Tooltip>
                  </Space>
                }
                valuePropName="checked"
              >
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prev, cur) =>
                prev?.rag_config?.retrieval_strategy !== cur?.rag_config?.retrieval_strategy
              }>
                {({ getFieldValue }) => {
                  const strategy = getFieldValue(['rag_config', 'retrieval_strategy']);
                  return (
                    <>
                      {strategy === 'contextual' && (
                        <Form.Item
                          name={['rag_config', 'use_contextual_embedding']}
                          label={
                            <Space>
                              上下文增强嵌入 (P1)
                              <Tooltip title="为每个chunk添加文档上下文后再生成embedding">
                                <QuestionCircleOutlined />
                              </Tooltip>
                            </Space>
                          }
                          valuePropName="checked"
                        >
                          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                        </Form.Item>
                      )}
                      {strategy === 'multi_query' && (
                        <Form.Item
                          name={['rag_config', 'multi_query_count']}
                          label="查询变体数量"
                        >
                          <InputNumber min={2} max={5} />
                        </Form.Item>
                      )}
                      {strategy === 'graph_rag' && (
                        <Form.Item
                          name={['rag_config', 'graph_rag_llm_model']}
                          label={
                            <Space>
                              实体抽取模型
                              <Tooltip title="用于 GraphRAG 实体和关系抽取的 LLM 模型">
                                <QuestionCircleOutlined />
                              </Tooltip>
                            </Space>
                          }
                        >
                          <Select
                            options={LLM_MODELS.map(m => ({
                              label: m.name,
                              value: m.model_id
                            }))}
                          />
                        </Form.Item>
                      )}
                    </>
                  );
                }}
              </Form.Item>
            </Panel>
          </Collapse>
        </Form>
      </Modal>

      <Drawer
        title={
          <Space>
            <BookOutlined />
            {selectedKB?.name}
          </Space>
        }
        open={detailDrawerOpen}
        onClose={() => {
          setDetailDrawerOpen(false);
          setUploadingFiles([]);
        }}
        width={800}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 拖拽上传区域 */}
          <Dragger
            accept={ACCEPTED_FILE_TYPES}
            multiple
            showUploadList={false}
            beforeUpload={(file, fileList) => {
              // 当选择多个文件时，只在最后一个文件时触发批量上传
              if (file === fileList[fileList.length - 1]) {
                handleBatchUpload(fileList as RcFile[]);
              }
              return false;
            }}
            style={{ padding: '20px 0' }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持 PDF、Word（.doc/.docx）、TXT、Markdown 格式，可批量上传多个文件
            </p>
          </Dragger>

          {/* 上传队列 */}
          {renderUploadQueue()}

          {/* 文档列表 */}
          <Card
            size="small"
            title={`文档列表 (${documents.length})`}
            extra={
              documents.some(d => d.status === 'processing') && (
                <Tag icon={<ReloadOutlined spin />} color="processing">
                  处理中，自动刷新
                </Tag>
              )
            }
          >
            <Table
              columns={docColumns}
              dataSource={documents}
              rowKey="id"
              size="small"
              locale={{ emptyText: renderDocEmpty() }}
            />
          </Card>
        </Space>
      </Drawer>

      {/* 知识图谱 Drawer */}
      <Drawer
        title={
          <Space>
            <ApartmentOutlined />
            知识图谱 - {graphKB?.name}
          </Space>
        }
        open={graphDrawerOpen}
        onClose={() => {
          console.log('[KnowledgeBasePage] 关闭图谱 Drawer');
          setGraphDrawerOpen(false);
          setGraphKB(null);
        }}
        width="90%"
        styles={{ body: { padding: 0, height: 'calc(100vh - 55px)' } }}
        destroyOnClose
      >
        {graphKB && (
          <KnowledgeGraph kbId={graphKB.id} kbName={graphKB.name} />
        )}
      </Drawer>
    </div>
  );
};

export default KnowledgeBasePage;
