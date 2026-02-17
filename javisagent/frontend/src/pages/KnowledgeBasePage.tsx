import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Modal, Form, Input, Select, Upload, message, Popconfirm, Tag, Space, Drawer } from 'antd';
import { PlusOutlined, UploadOutlined, DeleteOutlined, FileTextOutlined, BookOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { knowledgeApi } from '../services/knowledgeApi';
import type { KnowledgeBase, KBDocument } from '../types/knowledge';
import { EMBEDDING_MODELS } from '../types/knowledge';

const KnowledgeBasePage: React.FC = () => {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadKBs();
  }, []);

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

  const handleCreate = async (values: any) => {
    try {
      await knowledgeApi.createKB(values);
      message.success('创建成功');
      setCreateModalOpen(false);
      form.resetFields();
      loadKBs();
    } catch (e) {
      message.error('创建失败');
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

  const openDetail = async (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setDetailDrawerOpen(true);
    try {
      const docs = await knowledgeApi.listDocuments(kb.id);
      setDocuments(docs);
    } catch (e) {
      message.error('加载文档失败');
    }
  };

  const handleUpload = async (file: File) => {
    if (!selectedKB) return;
    setUploading(true);
    try {
      await knowledgeApi.uploadDocument(selectedKB.id, file);
      message.success('上传成功');
      const docs = await knowledgeApi.listDocuments(selectedKB.id);
      setDocuments(docs);
      loadKBs();
    } catch (e) {
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
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
    { title: '名称', dataIndex: 'name', key: 'name', render: (text: string, record: KnowledgeBase) => (
      <a onClick={() => openDetail(record)}><BookOutlined /> {text}</a>
    )},
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: 'Embedding 模型', dataIndex: 'embedding_model', key: 'embedding_model' },
    { title: '文档数', dataIndex: 'doc_count', key: 'doc_count' },
    { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (t: string) => new Date(t).toLocaleString() },
    { title: '操作', key: 'action', render: (_: any, record: KnowledgeBase) => (
      <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
        <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
      </Popconfirm>
    )},
  ];

  const docColumns = [
    { title: '文件名', dataIndex: 'filename', key: 'filename', render: (t: string) => <><FileTextOutlined /> {t}</> },
    { title: '类型', dataIndex: 'file_type', key: 'file_type' },
    { title: '大小', dataIndex: 'file_size', key: 'file_size', render: (s: number) => `${(s / 1024).toFixed(1)} KB` },
    { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => (
      <Tag color={s === 'completed' ? 'green' : s === 'processing' ? 'blue' : s === 'failed' ? 'red' : 'default'}>
        {s === 'completed' ? '已完成' : s === 'processing' ? '处理中' : s === 'failed' ? '失败' : '待处理'}
      </Tag>
    )},
    { title: '操作', key: 'action', render: (_: any, record: KBDocument) => (
      <Popconfirm title="确定删除？" onConfirm={() => handleDeleteDoc(record.id)}>
        <Button type="link" danger size="small">删除</Button>
      </Popconfirm>
    )},
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="知识库管理" extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          新建知识库
        </Button>
      }>
        <Table columns={columns} dataSource={kbs} rowKey="id" loading={loading} />
      </Card>

      <Modal title="新建知识库" open={createModalOpen} onCancel={() => setCreateModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="知识库名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="知识库描述" rows={3} />
          </Form.Item>
          <Form.Item name="embedding_model" label="Embedding 模型" initialValue="text-embedding-3-small">
            <Select options={EMBEDDING_MODELS.map(m => ({ label: m.name, value: m.model_id }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title={selectedKB?.name} open={detailDrawerOpen} onClose={() => setDetailDrawerOpen(false)} width={720}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Upload beforeUpload={(file) => { handleUpload(file); return false; }} showUploadList={false}>
            <Button icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
          </Upload>
          <Table columns={docColumns} dataSource={documents} rowKey="id" size="small" />
        </Space>
      </Drawer>
    </div>
  );
};

export default KnowledgeBasePage;
