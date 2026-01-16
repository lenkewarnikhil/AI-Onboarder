"""
Project view page - Documentation, Videos, and Chat interface
"""

import streamlit as st
import uuid
import os
from datetime import datetime
import threading
import asyncio

from lib.database import (
    get_project, get_documents_by_project, create_document,
    get_document_by_project_and_type, create_video, get_videos_by_document,
    update_video_status, update_document_status, delete_document_by_type,
    replace_document_safely, get_document_version_history
)
from lib.types import Document, Video
from lib.git import get_or_create_session, get_existing_session
from lib.tools import create_repo_tools
from lib.agents import create_doc_agents, QAAgent
from lib.agents.video_agent import generate_storyboard
from lib.video import generate_video_async
from lib.logger import create_logger

log = create_logger('PROJECT')

# Document type titles
DOC_TITLES = {
    'overview': 'Platform Overview',
    'how_it_works': 'How It Works',
    'training': 'Employee Training',
    'terms': 'Terms & Features',
    'user_flows': 'User Journeys',
    'troubleshooting': 'Troubleshooting Guide',
    'custom': 'Custom Document'
}

def generate_document_async(document_id: str, project_id: str, doc_type: str, title: str, project_md: str, github_url: str, old_doc_id: str = None):
    """
    Generate document in background
    
    Args:
        document_id: ID of the new document being generated
        old_doc_id: ID of the old document to replace (if regenerating)
    """
    try:
        log.info('=' * 80)
        log.info(f'DOCUMENT GENERATION START')
        log.info(f'Document ID: {document_id}')
        log.info(f'Old Doc ID: {old_doc_id}' if old_doc_id else 'New Document')
        log.info(f'Project ID: {project_id}')
        log.info(f'Doc Type: {doc_type}')
        log.info(f'GitHub URL: {github_url}')
        log.info('=' * 80)
        
        # Update status to generating
        update_document_status(document_id, 'generating')
        
        # Try to get existing session (reuse cloned repo from session system)
        context_only_mode = False
        repo_path = None
        
        try:
            # Check session system first
            session = get_existing_session(project_id, github_url)
            
            if session and os.path.exists(session.repo_path):
                log.info(f'✅ Using repository from active session: {session.repo_path}')
                repo_path = session.repo_path
            else:
                log.info('📋 No active session found - using PROJECT.md context-only mode')
                context_only_mode = True
        except Exception as e:
            log.warning(f'⚠️ Could not access repository: {e}')
            log.info('📋 Falling back to PROJECT.md context-only mode')
            context_only_mode = True
        
        # Generate document based on available resources
        if context_only_mode:
            # Generate from PROJECT.md only (no repo access)
            log.info('🔄 Generating from PROJECT.md context only')
            from lib.agents.doc_agents import DocAgent
            agent = DocAgent(doc_type, None)  # No repo tools
            content = agent.generate_doc(project_md, title, context_only=True)
        else:
            # Full mode with repo exploration
            log.info(f'🔄 Generating with full repository access: {repo_path}')
            from lib.agents.doc_agents import DocAgent
            repo_tools = create_repo_tools(repo_path)
            
            # Create only the specific agent needed (not all 12 types)
            agent = DocAgent(doc_type, repo_tools)
            
            content = agent.generate_doc(project_md, title, context_only=False)
        
        # Safely replace old document if regenerating
        if old_doc_id:
            replace_document_safely(old_doc_id, document_id, content, 'ready')
            log.info(f'✅ Document regenerated: {document_id} (archived old version: {old_doc_id})')
        else:
            # New document - just update with content
            update_document_status(document_id, 'ready', content=content)
            log.info(f'✅ Document ready: {document_id}')
        
    except Exception as e:
        log.error(f'❌ Document generation failed: {e}')
        import traceback
        traceback.print_exc()
        update_document_status(document_id, 'error', error_message=str(e))
        # Note: Old document is preserved if regeneration fails

def generate_video_async_wrapper(video_id: str, document_id: str, document: Document, color_scheme: str = 'ocean'):
    """Generate video in background"""
    try:
        log.info(f'Generating video for document: {document_id} with theme: {color_scheme}')
        
        # Generate storyboard
        update_video_status(video_id, 'generating')
        storyboard = generate_storyboard(document.title, document.content)
        
        # Generate video with asyncio
        async def gen():
            result = await generate_video_async(video_id, storyboard, color_scheme=color_scheme)
            
            # Update video in database
            from lib.database import get_connection
            import json
            conn = get_connection()
            cursor = conn.cursor()
            
            # Convert storyboard to JSON string
            storyboard_json = json.dumps(storyboard) if storyboard else None
            
            cursor.execute('''
                UPDATE videos 
                SET status = ?, video_url = ?, storyboard = ?
                WHERE id = ?
            ''', ('ready', result['videoUrl'], storyboard_json, video_id))
            
            conn.commit()
            conn.close()
            
            log.info(f'Video ready: {video_id}')
        
        # Run async function
        asyncio.run(gen())
        
    except Exception as e:
        log.error(f'Video generation failed: {e}')
        update_video_status(video_id, 'error', str(e))

def render(navigate_to, project_id: str):
    """Render project view page"""
    
    # Back button
    if st.button('← Back to Projects'):
        navigate_to('home')
    
    # Load project
    project = get_project(project_id)
    
    if not project:
        st.error('Project not found')
        return
    
    if project.status != 'ready':
        st.warning(f'Project is not ready yet. Status: {project.status}')
        return
    
    # Auto-generate Platform Overview on first view (if not exists)
    overview_doc = get_document_by_project_and_type(project.id, 'overview')
    if not overview_doc:
        st.info('🚀 **First Time Setup**: Auto-generating Platform Overview...')
        
        # Create pending overview document
        document_id = str(uuid.uuid4())
        overview = Document(
            id=document_id,
            project_id=project.id,
            type='overview',
            title='Platform Overview',
            content='',
            diagram_url=None,
            created_at=datetime.now().isoformat(),
            status='pending',
            error_message=None,
            version=1,
            updated_at=None,
            previous_version_id=None
        )
        create_document(overview)
        
        # Start background generation
        thread = threading.Thread(
            target=generate_document_async,
            args=(document_id, project.id, 'overview', 'Platform Overview', project.project_md, project.github_url),
            daemon=True
        )
        thread.start()
        
        st.success('✅ Platform Overview generation started!')
        import time
        time.sleep(2)
        st.rerun()
    
    # Header
    st.title(project.repo_name)
    st.caption(f'Commit: {project.commit_sha[:8]}')
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(['📄 Documents', '🎥 Videos', '💬 Chat'])
    
    with tab1:
        render_documents_tab(project)
    
    with tab2:
        render_videos_tab(project)
    
    with tab3:
        render_chat_tab(project)

def render_documents_tab(project):
    """Render documents tab"""
    
    st.subheader('Documentation')
    
    # Get existing documents
    docs = get_documents_by_project(project.id)
    
    # Auto-generate overview if no documents exist
    if not docs:
        st.info('🔄 No documents found. Auto-generating Platform Overview...')
        
        # Auto-generate overview document
        doc_id = str(uuid.uuid4())
        title = 'Platform Overview'
        doc_type = 'overview'
        
        create_document(doc_id, project.id, doc_type, title, status='generating')
        
        # Start background generation
        thread = threading.Thread(
            target=generate_document_async,
            args=(doc_id, project.id, doc_type, title, project.project_md, project.github_url)
        )
        thread.daemon = True
        thread.start()
        
        time.sleep(0.5)  # Brief pause for generation to start
        st.rerun()
        return
    
    # Document generation section
    with st.expander('➕ Generate New Document'):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            doc_type = st.selectbox(
                'Document Type',
                options=list(DOC_TITLES.keys()),
                format_func=lambda x: DOC_TITLES[x]
            )
        
        with col2:
            if st.button('Generate', type='primary', use_container_width=True):
                # Check if document already exists (except for custom)
                old_doc_id = None
                if doc_type != 'custom':
                    existing = get_document_by_project_and_type(project.id, doc_type)
                    if existing:
                        if existing.status == 'generating':
                            st.warning('⏳ This document is already being generated...')
                            st.stop()
                        elif existing.status == 'ready':
                            st.info(f'ℹ️ Regenerating (current version: {existing.version}). Old version will be preserved.')
                            # Keep old document ID for safe replacement
                            old_doc_id = existing.id
                
                title = DOC_TITLES[doc_type]
                
                # Create pending document first
                document_id = str(uuid.uuid4())
                document = Document(
                    id=document_id,
                    project_id=project.id,
                    type=doc_type,
                    title=title,
                    content='',
                    diagram_url=None,
                    created_at=datetime.now().isoformat(),
                    status='pending',
                    error_message=None,
                    version=1,  # Will be updated during safe replacement
                    updated_at=None,
                    previous_version_id=None
                )
                create_document(document)
                
                # Start background generation with old_doc_id for safe replacement
                thread = threading.Thread(
                    target=generate_document_async,
                    args=(document_id, project.id, doc_type, title, project.project_md, project.github_url, old_doc_id),
                    daemon=True
                )
                thread.start()
                
                st.success('✅ Document generation started!')
                st.info('🔄 Generating... The page will auto-refresh to show progress.')
                st.rerun()
    
    # Check if repository is available via session system
    session = get_existing_session(project.id, project.github_url)
    repo_available = session is not None and os.path.exists(session.repo_path) if session else False
    
    if not repo_available:
        st.markdown("""
        <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
            <span style="color: #92400e; font-size: 14px;">⚠️ <strong>Repository Unavailable</strong>: Documents will be generated from PROJECT.md context only</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
            <span style="color: #166534; font-size: 14px;">✅ <strong>Repository Available</strong>: Documents will be generated with full code exploration</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Load documents
    documents = get_documents_by_project(project.id)
    
    # Filter to show only current versions (exclude archived documents)
    # Archived documents have type prefixed with "_archived_"
    current_documents = [doc for doc in documents if not doc.type.startswith('_archived_')]
    
    # Check if any documents are generating (for auto-refresh)
    has_generating = any(doc.status == 'generating' or doc.status == 'pending' for doc in current_documents)
    if has_generating:
        st.info('⏳ Documents are being generated... This page will auto-refresh.')
        import time
        time.sleep(3)
        st.rerun()
    
    if not current_documents:
        st.info('No documents yet. Generate one above.')
    else:
        # Display PROJECT.md first (only if it's properly generated)
        if project.project_md and len(project.project_md.strip()) > 100 and not project.project_md.startswith('Okay, I'):
            with st.expander('📋 PROJECT.md', expanded=False):
                st.markdown(project.project_md)
        
        # Display only current versions of documents
        for doc in current_documents:
            # Status indicator
            status_emoji = {
                'pending': '⏳',
                'generating': '🔄',
                'ready': '✅',
                'error': '❌'
            }
            emoji = status_emoji.get(doc.status, '❓')
            
            # Build title with version info
            title_text = f'{emoji} {doc.title}'
            if doc.status == 'ready' and doc.version > 1:
                title_text += f' (v{doc.version})'
            # Don't show status in title anymore
            
            with st.expander(title_text):
                if doc.status == 'ready':
                    # Version and timestamp info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f'📅 Created: {doc.created_at[:10]}')
                    with col2:
                        if doc.updated_at:
                            st.caption(f'🔄 Updated: {doc.updated_at[:10]}')
                        else:
                            st.caption("🔄 Updated: 1st time")
                    with col3:
                        regeneration_count = doc.version - 1
                        st.caption(f'🔁 Regenerated: {regeneration_count} time{"s" if regeneration_count != 1 else ""}')
                    
                    # Version history link
                    if doc.previous_version_id or doc.version > 1:
                        if st.button(f'📜 View Version History ({doc.version} versions)', key=f'history_{doc.id}'):
                            # Toggle version history in session state
                            st.session_state[f'show_history_{doc.type}'] = not st.session_state.get(f'show_history_{doc.type}', False)
                            st.rerun()
                    
                    # Show version history if requested
                    if st.session_state.get(f'show_history_{doc.type}', False):
                        st.markdown('---')
                        st.subheader('📚 Version History')
                        versions = get_document_version_history(project.id, doc.type)
                        
                        # Display versions in a compact list with three-dots menu
                        for v in versions:
                            v_num = v.version
                            v_date = v.updated_at[:10] if v.updated_at else v.created_at[:10]
                            is_current = v.id == doc.id
                            
                            # Create columns for version info and actions
                            v_col1, v_col2, v_col3 = st.columns([3, 1, 1])
                            
                            with v_col1:
                                if is_current:
                                    st.markdown(f"**Version {v_num}** - {v_date} 🟢 *Current*")
                                else:
                                    st.markdown(f"**Version {v_num}** - {v_date}")
                            
                            with v_col2:
                                st.caption(f"{len(v.content)} chars")
                            
                            with v_col3:
                                # Three dots menu to expand version
                                if st.button('⋯', key=f'expand_v_{v.id}', help='View content'):
                                    # Toggle expanded state for this version
                                    expanded_key = f'expanded_version_{v.id}'
                                    st.session_state[expanded_key] = not st.session_state.get(expanded_key, False)
                                    st.rerun()
                            
                            # Show content if expanded
                            if st.session_state.get(f'expanded_version_{v.id}', False):
                                with st.container():
                                    st.markdown('---')
                                    st.markdown(v.content)
                                    st.markdown('---')
                        
                        if st.button('✖ Hide Version History', key=f'hide_history_{doc.id}'):
                            st.session_state[f'show_history_{doc.type}'] = False
                            st.rerun()
                    
                    st.markdown('---')
                    st.markdown(doc.content)
                    
                elif doc.status == 'generating':
                    st.info('🔄 Generating document... Please wait.')
                    st.spinner('Processing...')
                elif doc.status == 'pending':
                    st.info('⏳ Waiting to start generation...')
                elif doc.status == 'error':
                    st.error(f'❌ Generation failed: {doc.error_message}')
                    st.caption(f'Created: {doc.created_at[:10]}')
                    if doc.version > 1:
                        st.info('ℹ️ Previous version is still available (preserved on failure)')

def render_videos_tab(project):
    """Render videos tab"""
    
    st.subheader('Video Briefings')
    st.caption('Generate automated video briefings from documentation')
    
    # Load documents
    documents = get_documents_by_project(project.id)
    
    if not documents:
        st.info('Generate documents first before creating videos.')
        return
    
    # Video generation section
    with st.expander('➕ Generate New Video', expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            doc_options = {doc.id: f"{doc.title}" for doc in documents}
            selected_doc_id = st.selectbox(
                'Select Document',
                options=list(doc_options.keys()),
                format_func=lambda x: doc_options[x]
            )
        
        with col2:
            color_scheme = st.selectbox(
                'Visual Theme',
                options=['ocean', 'minimal', 'midnight'],
                format_func=lambda x: {
                    'ocean': '🌊 Ocean Blue',
                    'minimal': '✨ Clean & Minimal',
                    'midnight': '🌙 Midnight Purple'
                }[x]
            )
        
        with col3:
            if st.button('Generate Video', type='primary', use_container_width=True):
                # Get document
                document = next((d for d in documents if d.id == selected_doc_id), None)
                if not document:
                    st.error('Document not found')
                    return
                
                # Create video record
                video_id = str(uuid.uuid4())
                video = Video(
                    id=video_id,
                    document_id=selected_doc_id,
                    status='pending',
                    video_url=None,
                    transcript=None,
                    storyboard=None,
                    created_at=datetime.now().isoformat()
                )
                
                create_video(video)
                
                # Start background generation
                thread = threading.Thread(
                    target=generate_video_async_wrapper,
                    args=(video_id, selected_doc_id, document, color_scheme),
                    daemon=True
                )
                thread.start()
                
                st.success('✅ Video generation started')
                st.info('This will take 3-5 minutes. Refresh to see progress.')
                st.rerun()
    
    # Display videos grouped by document
    st.markdown('---')
    st.subheader('Generated Videos')
    
    for document in documents:
        videos = get_videos_by_document(document.id)
        
        if videos:
            st.markdown(f'**{document.title}**')
            
            for video in videos:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if video.status == 'ready' and video.video_url:
                        st.video(f'public{video.video_url}')
                    else:
                        status_icons = {
                            'pending': '🟡',
                            'generating': '🔵',
                            'ready': '🟢',
                            'error': '🔴'
                        }
                        icon = status_icons.get(video.status, '⚪')
                        st.info(f'{icon} Status: {video.status}')
                
                with col2:
                    st.caption(f'Created: {video.created_at[:10]}')
                
                with col3:
                    if video.status == 'error' and video.error_message:
                        st.error(f'Error: {video.error_message[:50]}...')
            
            st.markdown('---')
    
    # Auto-refresh for pending videos
    all_videos = []
    for doc in documents:
        all_videos.extend(get_videos_by_document(doc.id))
    
    if any(v.status in ['pending', 'generating'] for v in all_videos):
        st.info('🔄 Videos are being generated... (Auto-refreshing every 10 seconds)')
        import time
        time.sleep(10)
        st.rerun()

def render_chat_tab(project):
    """Render ChatGPT-style chat interface"""
    
    # Initialize chat history in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = None
    
    # Initialize cached QA agent (None means it will be created on first message)
    if 'qa_agent' not in st.session_state:
        st.session_state.qa_agent = None
    
    # Initialize or refresh context mode flag based on current session status
    session = get_existing_session(project.id, project.github_url)
    st.session_state.chat_context_mode = session is None
    
    # Clear chat button in corner
    if len(st.session_state.chat_messages) > 0:
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_chat_btn"):
                st.session_state.chat_messages = []
                # Clear the cached agent to start fresh conversation
                st.session_state.qa_agent = None
                log.info('Chat history and agent cleared')
                st.rerun()
    
    # Welcome message if chat is empty
    if len(st.session_state.chat_messages) == 0:
        st.markdown("""
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; 
                    padding: 32px; margin-bottom: 24px; text-align: center;">
            <h2 style="color: #0f172a; margin: 0 0 12px 0; font-size: 24px;">💬 Chat with Your Codebase</h2>
            <p style="font-size: 15px; color: #64748b; margin: 0;">
                Ask me anything about this repository. I can explain code, architecture, and functionality.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Example questions
        st.markdown("**💡 Example questions:**")
        
        col1, col2 = st.columns(2)
        
        example_questions = [
            "What is this project about?",
            "Explain the main architecture",
            "How does authentication work?",
            "What are the key features?",
            "Show me the database schema",
            "How do I run this locally?"
        ]
        
        for i, question in enumerate(example_questions):
            col = col1 if i % 2 == 0 else col2
            with col:
                # Use a unique key and handle click properly
                if st.button(question, key=f"example_q_{i}", use_container_width=True, type="secondary"):
                    # Add user message immediately
                    st.session_state.chat_messages.append({
                        'role': 'user',
                        'content': question
                    })
                    # Add thinking indicator
                    st.session_state.chat_messages.append({
                        'role': 'assistant',
                        'content': '__THINKING__'
                    })
                    # Store for processing in next render
                    st.session_state.pending_message = question
                    st.rerun()
        
        st.markdown("---")
    
    # Chat messages container with auto-scroll
    chat_container = st.container()
    
    with chat_container:
        # Display all messages
        for idx, message in enumerate(st.session_state.chat_messages):
            if message['role'] == 'user':
                # User message on the RIGHT
                col1, col2 = st.columns([3, 7])
                with col2:
                    st.markdown(f"""
                    <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; 
                                padding: 12px 16px; margin: 8px 0; border-left: 3px solid #ef4444;">
                        <div style="color: #991b1b; font-weight: 600; font-size: 13px; margin-bottom: 4px;">👤 You</div>
                        <div style="color: #1e293b;">{message['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Assistant message on the LEFT
                col1, col2 = st.columns([7, 3])
                with col1:
                    # Check if this is a thinking indicator
                    if message['content'] == '__THINKING__':
                        st.markdown("""
                        <div style="background: #eff6ff; border: 1px solid #dbeafe; border-radius: 12px; 
                                    padding: 12px 16px; margin: 8px 0; border-left: 3px solid #3b82f6;">
                            <div style="color: #1e40af; font-weight: 600; font-size: 13px; margin-bottom: 4px;">🤖 AI Assistant</div>
                            <div style="color: #64748b; line-height: 1.6;">💭 Thinking and analyzing your question...</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background: #eff6ff; border: 1px solid #dbeafe; border-radius: 12px; 
                                    padding: 12px 16px; margin: 8px 0; border-left: 3px solid #3b82f6;">
                            <div style="color: #1e40af; font-weight: 600; font-size: 13px; margin-bottom: 4px;">🤖 AI Assistant</div>
                            <div style="color: #1e293b; line-height: 1.6;">{message['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Auto-scroll to bottom using JavaScript
    st.markdown("""
    <script>
        // Auto-scroll chat to bottom
        setTimeout(function() {
            var elements = window.parent.document.querySelectorAll('[data-testid="stVerticalBlock"]');
            if (elements.length > 0) {
                var chatContainer = elements[elements.length - 1];
                chatContainer.scrollTo({
                    top: chatContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }, 100);
    </script>
    """, unsafe_allow_html=True)
    
    # Check if we need to process a pending message
    if 'pending_message' in st.session_state:
        pending_msg = st.session_state.pending_message
        del st.session_state.pending_message
        process_chat_message(project, pending_msg)
        st.rerun()
    
    # Show context warning if in fallback mode
    if st.session_state.get('chat_context_mode', False):
        st.markdown("""
        <div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; 
                    padding: 10px 16px; margin-bottom: 12px;">
            <span style="color: #92400e; font-weight: 500; font-size: 13px;">
                ⚠️ Context Mode: Using PROJECT.md summary (repository session unavailable)
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    # Chat input at bottom
    prompt = st.chat_input('💭 Ask a question about the codebase...', key='chat_input')
    
    if prompt:
        # Add user message immediately
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': prompt
        })
        
        # Add thinking indicator
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': '__THINKING__'
        })
        
        # Store message for processing in next render
        st.session_state.pending_message = prompt
        st.rerun()

def process_chat_message(project, user_message):
    """Process chat message and get AI response"""
    try:
        # Remove thinking indicator if present
        if st.session_state.chat_messages and st.session_state.chat_messages[-1].get('content') == '__THINKING__':
            st.session_state.chat_messages.pop()
        
        # Check for existing session WITHOUT creating new one
        context_only = False
        repo_path = None
        
        session = get_existing_session(project.id, project.github_url)
        
        if session and os.path.exists(session.repo_path):
            # Valid session exists
            st.session_state.chat_session_id = session.session_id
            st.session_state.chat_context_mode = False  # Update flag - we have repo
            repo_path = session.repo_path
            log.info(f'Chat using repository at: {repo_path}')
        else:
            # No valid session - use PROJECT.md fallback
            context_only = True
            st.session_state.chat_context_mode = True  # Update flag - using fallback
            log.info(f'No valid session found. Chat using PROJECT.md context only')
        
        # Reuse existing agent if available, otherwise create new one
        # Agent is cached in session_state to maintain conversation context
        if st.session_state.qa_agent is None:
            log.info('Creating new QA agent (first message or after clear)')
            # Create agent with appropriate mode
            if context_only:
                repo_tools = None  # No tools needed for context-only mode
            else:
                repo_tools = create_repo_tools(repo_path)
            
            st.session_state.qa_agent = QAAgent(repo_tools, project.project_md, context_only=context_only)
        else:
            log.info(f'Reusing existing QA agent [{st.session_state.qa_agent.session_id}]')
        
        # Get response using cached agent (maintains conversation context internally)
        response = st.session_state.qa_agent.chat(st.session_state.chat_messages)
        
        # Add assistant message (replaces thinking indicator)
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': response
        })
        
    except Exception as e:
        # Remove thinking indicator if present
        if st.session_state.chat_messages and st.session_state.chat_messages[-1].get('content') == '__THINKING__':
            st.session_state.chat_messages.pop()
        
        error_msg = f'Error: {str(e)}'
        log.error(error_msg)
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': f'❌ {error_msg}'
        })
